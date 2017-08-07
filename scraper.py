import click
import datetime
import json
import os
import sys
import reddit as reddit_control
import tigsource as tig_control
import time
import urllib


DESKTOP_IDENTIFIER = 'desktop*'
SETTINGS = None


def download_image_from_url(url, directory, filename=None):
    if filename is None:
        filename = url.split('/')[-1]

    # check if filename exists, if so: append a unique number to it
    base_filename = filename
    x = 0
    while filename in os.listdir(directory):
        x += 1
        filename = base_filename + str(x)

    try:
        urllib.request.urlretrieve(url, os.path.join(directory, filename))
    except (OSError, urllib.error.HTTPError):
        print('[ERROR] Could not download: ' + url)


def get_scraper_settings(settings_filename):
    global SETTINGS

    if SETTINGS is None:
        with open(settings_filename) as settings_file:
            SETTINGS = json.load(settings_file)
    return SETTINGS


def create_folder(export_folder):
    try:
        os.makedirs(export_folder, exist_ok=False)
    except OSError:
        if (os.listdir(export_folder)):
            print('[ERROR] Export folder already exists')


def get_export_folder(prefix='export'):
    export_directory = click.prompt('Export directory', type=str, default=DESKTOP_IDENTIFIER)

    # Find desktop path
    if export_directory == DESKTOP_IDENTIFIER:
        if sys.platform.startswith('win'):
            export_directory = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        elif sys.platform.startswith('linux'):
            export_directory = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
        else:
            # TODO apple
            print("Cannot find desktop, using working directory")
            export_directory = os.getcwd()

    # Create export folder, with timestamp
    t = time.time()
    timestamp = datetime.datetime.fromtimestamp(t).strftime('%Y%m%d_%H%M%S')
    return os.path.join(export_directory, prefix + timestamp)


def scrape_reddit(settings, export_folder, verbose=False):
    subreddits = settings['reddit']['subreddits']

    # Retrieve reddit posts
    # TODO different date ranges
    reddit_posts = []
    with click.progressbar(subreddits, label='Scanning subreddits') as bar:
        for subreddit in bar:
            subreddit_posts = reddit_control.get_posts_by_date(
                subreddit=subreddit['name'],
                min_score=subreddit['min_karma'],
                days=7,
            )
            reddit_posts += subreddit_posts

    # Extract post data and download files
    post_num = 0
    post_info = ''

    with click.progressbar(reddit_posts, label='Downloading posts') as bar:
        for post in bar:
            post_num += 1
            try:
                post_url = post['url']
                post_domain = post['domain']
                
                if post_domain == 'gfycat.com':
                    post_url = post_url[:8] + 'zippy.' + post_url[8:] + '.webm'
                if post_url.endswith('gifv'):
                    post_url = post_url[:-4] + 'mp4'

                _, extension = os.path.splitext(post_url)
                if extension is not None:
                    download_image_from_url(post_url, export_folder, 
                        str(post_num) + extension)
                else:
                    download_image_from_url(post_url, export_folder)

                post_info += "{:>3}\t{}\n{}\n{}\n\n".format(
                    post_num, post['author'], 
                    post['permalink'].encode('utf-8'), 
                    post_url)
            except (FileNotFoundError, OSError) as e:
                pass

    # Export post data
    # TODO sort posts by highest karma
    with open(os.path.join(export_folder, 'export_reddit.json'), 'w') as f:
        json.dump(reddit_posts, f, indent=4)

    # Export post_info
    with open(os.path.join(export_folder, 'export_reddit.txt'), 'w') as f:
        f.write(post_info)


def scrape_tigsource(settings, export_folder):
    topics = settings['tigsource']['topics']
    
    images = []
    for topic in topics:
        images += tig_control.get_posts_by_date(topic)

    for image_url in images:
        download_image_from_url(image_url, export_folder)

@click.group()
def scraper():
    pass


@scraper.command()
def all():
    export_folder = get_export_folder()
    create_folder(export_folder)
    # create_folder(export_folder, reddit)

    settings = get_scraper_settings('settings.json')

    # perform scrapes
    scrape_reddit(settings, export_folder)
    scrape_tigsource(settings, export_folder)


@scraper.command()
def reddit():
    export_folder = get_export_folder(prefix='reddit')
    create_folder(export_folder)
    settings = get_scraper_settings('settings.json')

    scrape_reddit(settings, export_folder)


@scraper.command()
def tigsource():
    export_folder = get_export_folder(prefix='tigsource')
    create_folder(export_folder)
    settings = get_scraper_settings('settings.json')

    scrape_tigsource(settings, export_folder)


if __name__ == "__main__":
    scraper()
