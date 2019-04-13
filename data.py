import os
import urllib.request as req
import urllib.error as urlerr

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import util

SPOTIFY_USERNAME = 'spotify'
# SPOTIFY_USERNAME = 'lyoaqbt6veuxjxk5jwappooa3'
OUT_DIR = './out/data/'
IMAGE_LIST_FILENAME = 'images.lst'
DOWNLOAD_IMAGES = True


def spotipy_iter(sp, response):
    for item in response['items']:
        yield item
    
    while response['next']:
        response = sp.next(response)
        for item in response['items']:
            yield item

def create_album_dict(sp, username):
    user_playlists = sp.user_playlists(SPOTIFY_USERNAME)
    album_dict = {}

    for playlist in spotipy_iter(sp, user_playlists):
        playlist_id = playlist['id']
        playlist = sp.user_playlist(SPOTIFY_USERNAME, playlist_id=playlist_id)

        for track in spotipy_iter(sp, playlist['tracks']):
            # weird edge case where this value is None
            if not track['track']:
                continue

            album = track['track']['album']
            album_id = album['id']

            # some albums don't have images
            if not album['images']:
                continue 

            # widest image is always first
            album_image_url = album['images'][0]['url']

            if album_id in album_dict:
                continue

            album_dict[album_id] = album_image_url
    
    return album_dict

def write_to_file(image_urls, output_file):
    dir_path = os.path.dirname(output_file)
    util.makedirs(dir_path)

    with open(output_file, 'w') as fp:
        fp.writelines([i + "\n" for i in image_urls])

def download_image(out_dir, album_id, album_image):
    # just in case

    filename = '%s.jpeg'%album_id
    filepath = os.path.join(out_dir, '%s'%filename)

    req.urlretrieve(album_image, filepath)

def scrape_album_art(download_images=False):
    # authorize
    auth = SpotifyClientCredentials()
    token_info = auth.get_access_token()

    # create our client
    sp = spotipy.Spotify(token_info)
    
    # start our requests 
    album_dict = create_album_dict(sp, SPOTIFY_USERNAME)

    # write our image url list to a file
    write_to_file(album_dict.values(), os.path.join(OUT_DIR, IMAGE_LIST_FILENAME))

    # check if we need to download all of these guys
    if not download_images:    
        return 

    # download all of the images in our image list
    util.makedirs(OUT_DIR)
    for album_id, album_url in album_dict.items():
        try:
            download_image(OUT_DIR, album_id, album_url)
        except (urlerr.HTTPError, urlerr.ContentTooShortError):
            print('Could not retrieve album %s'%album_id)


if __name__ == '__main__':
    scrape_album_art(download_images=DOWNLOAD_IMAGES)