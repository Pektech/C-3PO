import re
from datetime import datetime, timedelta
from logging import getLogger

from c3po.api.dto import artist_dto, post_dto, song_dto
from c3po.api.service.paginate import get_paginated_response
from c3po.db.base import session_factory, session_scope
from c3po.db.models.artist import ArtistGenre, ArtistSong
from c3po.db.models.link import Link
from c3po.db.models.user import UserPosts

LOG = getLogger(__name__)


def format(session, post):
    link = post.link
    song = link.song
    artists = [
        artist_song.artist
        for artist_song in session.query(ArtistSong)
        .filter(ArtistSong.song == song)
        .all()
    ]
    genres = []
    for artist in artists:
        artist_genres = [
            artist_genre.genre
            for artist_genre in session.query(ArtistGenre)
            .filter(ArtistGenre.artist == artist)
            .all()
        ]
        genres += artist_genres

    return {
        "link": link.url,
        "post_count": link.post_count,
        "postdata": post_dto.dump(post),
        "metadata": {
            "song": song_dto.dump(link.song),
            "artists": [artist_dto.dump(artist) for artist in artists],
            "genre": [genre.name for genre in genres],
        },
    }


def post_genre_filter(post, query_genre):

    if not query_genre or not query_genre.strip():
        return post

    post_genres = post["metadata"]["genre"]
    if any(re.search(query_genre, genre) for genre in post_genres):
        return post


class FeedService:
    @staticmethod
    def get_posts_in_interval(
        from_=datetime.now() - timedelta(days=3), to_=datetime.now()
    ):
        try:
            session = session_factory()
            posts = (
                session.query(UserPosts)
                .filter(UserPosts.share_date >= from_)
                .filter(UserPosts.share_date <= to_)
                .all()
            )

            return posts, 200

        except BaseException:
            LOG.error(
                f"Failed to fetch data with params from_ = {from_}, to_ = {to_}. Try later.",
                exc_info=True,
            )
            response_object = {
                "status": "fail",
                "message": "Try again",
            }
            return response_object, 500

    @staticmethod
    def get_latest_posts(url, start, limit, genre_):
        with session_scope() as session:
            try:
                total = session.query(UserPosts).count()
                posts = (
                    session.query(UserPosts)
                    .filter(UserPosts.share_date <= datetime.now())
                    .order_by(UserPosts.share_date.desc())
                    .offset(start)
                    .limit(limit)
                    .all()
                )
                paginated_response = get_paginated_response(
                    posts, url, total, start, limit
                )

                formatted_posts = [
                    format(session, post) for post in paginated_response["posts"]
                ]

                paginated_response["posts"] = [
                    post_genre_filter(post, genre_)
                    for post in formatted_posts
                    if post_genre_filter(post, genre_) is not None
                ]

                return paginated_response, 200

            except BaseException:
                LOG.error(
                    f"Failed to fetch data with param start = {start}, limit = {limit}. Try later.",
                    exc_info=True,
                )
                response_object = {
                    "status": "fail",
                    "message": "Try again",
                }
                return response_object, 500

    @staticmethod
    def get_popular_posts(url, n, start, limit, genre_):
        """ Retrieves the most popular posts in the past n days"""
        with session_scope() as session:
            try:
                all_posts = (
                    session.query(UserPosts)
                    .filter(UserPosts.share_date <= datetime.now() + timedelta(days=1))
                    .filter(UserPosts.share_date >= datetime.now() - timedelta(days=n))
                    .order_by(UserPosts.likes_count.desc())
                )
                total = all_posts.count()
                posts = all_posts.offset(start).limit(limit).all()

                paginated_response = get_paginated_response(
                    posts, url, start=start, limit=limit, total=total
                )

                formatted_posts = [
                    format(session, post) for post in paginated_response["posts"]
                ]

                paginated_response["posts"] = [
                    post_genre_filter(post, genre_)
                    for post in formatted_posts
                    if post_genre_filter(post, genre_) is not None
                ]

                return paginated_response, 200

            except BaseException:
                LOG.error(
                    f"Failed to fetch data with param n = {n}, start = {start}, limit = {limit} . Try later.",
                    exc_info=True,
                )
                response_object = {
                    "status": "fail",
                    "message": "Try again",
                }
                return response_object, 500

    @staticmethod
    def get_frequent_posts(url, start, limit, genre_):
        with session_scope() as session:
            try:
                total = session.query(UserPosts).count()
                posts = (
                    session.query(UserPosts)
                    .filter(UserPosts.share_date <= datetime.now())
                    .join(UserPosts.link)
                    .order_by(Link.post_count.desc())
                    .offset(start)
                    .limit(limit)
                    .all()
                )

                paginated_response = get_paginated_response(
                    posts, url, total, start=start, limit=limit
                )
                formatted_posts = [
                    format(session, post) for post in paginated_response["posts"]
                ]

                paginated_response["posts"] = [
                    post_genre_filter(post, genre_)
                    for post in formatted_posts
                    if post_genre_filter(post, genre_) is not None
                ]

                return paginated_response, 200

            except BaseException:
                LOG.error(
                    f"Failed to fetch data with param limit_ = {limit} and genre_ = {genre_}. Try later.",
                    exc_info=True,
                )
                response_object = {
                    "status": "fail",
                    "message": "Try again",
                }
                return response_object, 500
