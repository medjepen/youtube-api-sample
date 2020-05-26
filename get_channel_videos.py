#!/usr/bin/python
import argparse
import os
import pandas as pd
import requests
import time
from apiclient.discovery import build
from apiclient.errors import HttpError

API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
API_URL = 'https://www.googleapis.com/youtube/v3'

def _batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

def get_channel_videos(playlist_id, input_file='video_ids.csv'):
    '''
    [TODO: 場合分けしよう]
    できれば場合分けもしたい．
    channelIDがわかっている  -> playlistIDを取得 or "UC" を "UU" に置換？
    playlistIDがわかっている -> videoIDを取得する
    videoIDがわかっている    -> videoの詳細取得
    '''

    # プレイリストID投げると動画のIDリスト(タイトル含む)とそのdfが返ってくる
    video_info, video_df = _get_video_ids(playlist_id)
    
    # 動画のIDリストを外部csvで入力するときはこっち
    # video_df = pd.read_csv(input_file, encoding='utf-8', index_col=False, dtype=object)
    # video_info = video_df.values.tolist()
    
    # 動画詳細取得
    print("list: %s" % len(video_info))
    _get_video_details(video_info)


def _get_video_ids(playlist_id):
    info = []
    # Get channel video's ID
    request = youtube.playlistItems().list(
        playlistId=playlist_id,
        part='snippet,contentDetails',
        maxResults=50)
    
    print('<INFO> GET Video IDs in list %s' % playlist_id)
    
    while request:
        # [TODO: スリープ多くないです？]
        # 1リクエスト毎に1秒待機
        # タイムアウト対策
        time.sleep(1)
        response = request.execute()
        # Print information about each video.
        for item in response['items']:
            title = item['snippet']['title']
            video_id = item['contentDetails']['videoId']
            info.append([video_id, title])

        request = youtube.playlistItems().list_next(request, response)
    
    video_df = pd.DataFrame(info, columns=['videoId', 'title'], index=None)
    video_df.to_csv('video_ids.csv', index=None, encoding='utf-8')
    print('<INFO> Done.')

    return info, video_df

def _get_video_details(video_id):
    info = []
    p = 0
    num = len(video_id)
    # 1リクエスト50本ずつ処理
    for chunk in _batch(video_id, 50):
        p += len(chunk)
        _ids = ",".join(map(lambda x: x[0], chunk))

        response = youtube.videos().list(
        part='id,snippet,contentDetails,statistics',
        id=_ids
        ).execute()

        for item in response['items']:
            _id = item['id']
            title = item['snippet']['title']
            description = item['snippet']['description']
            published_at = item['snippet']['publishedAt']
            duration = item['contentDetails']['duration']
            caption = item['contentDetails']['caption']
            # staticticsの各パラメータが欠損値のとき，-1を入れる
            views = item['statistics'].get('viewCount', -1)
            likes = item['statistics'].get('likeCount', -1)
            dislikes = item['statistics'].get('dislikeCount', -1)
            favorites = item['statistics'].get('favoriteCount', -1)
            comments = item['statistics'].get('commentCount', -1)

            info.append([
                _id, title, description, published_at, 
                duration, caption, 
                views, likes, dislikes, favorites, comments])
        
        print('<INFO> Progress in <%s/%s>' % (p,num))
        details_df = pd.DataFrame(info, columns=[
                        'videoId', 'title', 'description', 'publishedAt', 'duration', 'caption', 'viewCount', 'likeCount', 'dislikeCount', 'favoriteCount', 'commentCount'
                        ], index=None)
        details_df.to_csv('channel_video_lists.csv', index=None, encoding='utf-8')
        if (p % 500 == 0):
            # 500本ごとにスリープする,タイムアウト対策
            time.sleep(5)

    print('<INFO> Done.')
    return details_df

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--channel_id', help='チャンネルのプレイリストID', required=True)
    parser.add_argument('-i', '--api_key', help='APIキー', required=True)
    args = parser.parse_args()

    youtube = build(API_SERVICE_NAME, API_VERSION, developerKey=args.api_key)
    get_channel_videos(args.channel_id)

