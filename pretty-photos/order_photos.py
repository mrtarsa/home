
import datetime as dt
import random
import typing as _t
from argparse import ArgumentParser
from pathlib import Path

import ffmpeg
from PIL import Image

from utils import copy_file
from utils import get_console_logger
from utils import get_extension_from_path
from utils import try_mkdir


# Files with different extension will be skipped
_PHOTO_EXTENSIONS = ['JPG', 'jpg', 'JPEG', 'jpeg', 'PNG', 'png']
_VIDEO_EXTENSIONS = ['MOV', 'mov']

# If change FILE_TIME_FMT, then also change DATE_SPLIT_CHAR and DATE_TIME_SPLIT_CHAR
_FILE_TIME_FMT = '%Y-%m-%d_%H:%M:%S'
_DATE_SPLIT_CHAR = _FILE_TIME_FMT.split('%Y')[1].split('%m')[0]
_DATE_TIME_SPLIT_CHAR = _FILE_TIME_FMT.split('%Y-%m-%d')[1].split('%H:%M:%S')[0]

# Common prefix is used for interpolation, only photos that begin with COMMON_PREFIX can be interpolated
_COMMON_INTERPOLATION_PREFIX = 'IMG_'
_INTERPOLATED_SUFFIX = '_interpolated_time'

# Whether to split output files into separate directories
_SPLIT_INTO_YEARS = True

_LOGGER = get_console_logger('pretty-photos')


def get_photo_creation_time(path: Path) -> str:
    """Extract creation time from photo properties"""
    return Image.open(path)._getexif()[36867]


def get_video_creation_time(path: Path) -> str:
    """Extract creation time from video properties"""
    video_streams = ffmpeg.probe(path)['streams']
    video_tags = video_streams[0]['tags']
    return video_tags['creation_time'][:19]


def parse_photo_times(input_dir: Path) -> _t.Dict[Path, str]:
    num_dates_found = 0
    num_dates_missing = 0
    photo_times = {}
    for photo_path in input_dir.iterdir():

        if not photo_path.is_file():
            _LOGGER.warning(f'Skip [path={photo_path}] since not a file ...')
            continue

        photo_ext = get_extension_from_path(photo_path)

        if photo_ext in _PHOTO_EXTENSIONS:
            try:
                photo_time = get_photo_creation_time(photo_path)
                photo_time = photo_time[:10].replace(':', _DATE_SPLIT_CHAR) + photo_time[10:]
                photo_time = photo_time.replace(' ', _DATE_TIME_SPLIT_CHAR)

            except (KeyError, TypeError):
                photo_time = None
                num_dates_missing += 1
                _LOGGER.info(f'PARSE: Found [time={photo_time}] for [photo={photo_path}]')

            else:
                num_dates_found += 1
                _LOGGER.info(f'PARSE: Missing time for [photo={photo_path}]')

        # Order videos as well
        elif photo_ext in _VIDEO_EXTENSIONS:
            video_time = get_video_creation_time(photo_path)
            video_time = video_time.replace('T', _DATE_TIME_SPLIT_CHAR)
            # Treat video as photo from now on
            photo_time = video_time

        else:
            _LOGGER.info(f'PARSE: Could not process photo with [extension={photo_ext}]')
            continue

        photo_times[photo_path] = photo_time

    _LOGGER.info(
        f'FOUND dates: {num_dates_found} '
        f'MISSING dates: {num_dates_missing}\n'
    )

    return photo_times


def is_valid_for_interpolation(photo_path: Path) -> bool:
    """Only photos with specific names are valid for interpolation"""
    try:
        int(photo_path.stem.split(_COMMON_INTERPOLATION_PREFIX)[1].split('.')[0])
    except (IndexError, ValueError, TypeError):
        return False
    return True


def get_random_time_between(min_time: str, max_time: str) -> str:
    """Get random time between boundaries"""
    _LOGGER.info(f'Get random time between [min_time={min_time}] and [max_time={max_time}] ...')
    # Add and subtract one second, so not to duplicate times
    min_ts = int(dt.datetime.strptime(min_time, _FILE_TIME_FMT).timestamp()) + 1
    max_ts = int(dt.datetime.strptime(max_time, _FILE_TIME_FMT).timestamp()) - 1
    if max_ts < min_ts:
        raise ValueError(f'Could not get time between [min_time={min_time}] and [max_time={max_time}]')
    time_between = dt.datetime.utcfromtimestamp(random.randint(min_ts + 1, max_ts - 1))
    return time_between.strftime(_FILE_TIME_FMT)


def get_year_from_time(time: str) -> int:
    return dt.datetime.strptime(time, _FILE_TIME_FMT).year


def try_remove_interpolated_suffix(time: str) -> str:
    if not time.endswith(_INTERPOLATED_SUFFIX):
        return time
    return time.split(_INTERPOLATED_SUFFIX)[0]


def interpolate_photo_times(photo_times: _t.Dict[Path, str]) -> _t.Dict[Path, str]:
    """Interpolate missing photo time based on photo order, f.e IMG_1433"""

    sorted_photos = sorted(photo_times.keys())

    num_interpolated = 0
    num_failed = 0
    for photo_ind, photo_path in enumerate(sorted_photos):
        photo_time = photo_times[photo_path]

        if photo_time is not None:
            continue

        if not is_valid_for_interpolation(photo_path):
            _LOGGER.info(f'INTERPOLATE: Skip not valid for interpolation [photo={photo_path}]')
            continue

        # Find nearest previous neighbor
        prev_time = None
        for prev_photo in reversed(sorted_photos[:photo_ind]):
            if not is_valid_for_interpolation(prev_photo):
                continue

            prev_time = photo_times[prev_photo]
            if prev_time is not None:
                break

        if prev_time is None:
            _LOGGER.info(f'INTERPOLATE: Could not find previous time for [photo={photo_path}]')
            num_failed += 1
            continue

        # Find nearest next neighbor
        next_time = None
        for next_photo in sorted_photos[photo_ind + 1:]:
            if not is_valid_for_interpolation(next_photo):
                continue

            next_time = photo_times[next_photo]
            if next_time is not None:
                break

        if next_time is None:
            _LOGGER.info(f'INTERPOLATE: Could not find next time for [photo={photo_path}]')
            num_failed += 1
            continue

        # Previous time can already be interpolated
        prev_time = try_remove_interpolated_suffix(prev_time)

        try:
            # NOTE: Sleeping time is possible output :)
            photo_time = get_random_time_between(prev_time, next_time)
        except ValueError:
            _LOGGER.info(f'INTERPOLATE: Could not find time for [photo={photo_path}]')
            num_failed += 1
            continue

        photo_times[photo_path] = photo_time + _INTERPOLATED_SUFFIX
        num_interpolated += 1
        _LOGGER.info(f'INTERPOLATE: Set [time={photo_time}] for [photo={photo_path}]')

    _LOGGER.info(
        f'INTERPOLATED times: {num_interpolated} '
        f'FAILED times: {num_failed}\n'
    )

    return photo_times


def save_photos_with_times(photo_times: _t.Dict[Path, str], output_dir: Path) -> None:
    """Save photos with different names that include their time into separate directory"""

    photos_dir_with_times = try_mkdir(output_dir)
    photos_dir_without_times = try_mkdir(output_dir / 'without-time')

    _LOGGER.info(f'Will save photos with time into [directory={photos_dir_with_times}]')
    _LOGGER.info(f'Will save photos without time into [directory={photos_dir_without_times}]')
    _LOGGER.info('...')

    for photo_path, photo_time in photo_times.items():
        photo_ext = get_extension_from_path(photo_path)

        if photo_time is not None:
            photo_name = f'{photo_time}.{photo_ext}'

            output_path = photos_dir_with_times
            if _SPLIT_INTO_YEARS:
                try:
                    photo_year = get_year_from_time(try_remove_interpolated_suffix(photo_time))
                except ValueError:
                    raise
                output_path = try_mkdir(output_path / str(photo_year))
            output_path /= photo_name

        else:
            photo_name = f'{photo_path.stem}.{photo_ext}'
            output_path = photos_dir_without_times / photo_name

        copy_file(photo_path, output_path)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument('--input-dir', required=True, type=str, help='Directory with input photos')
    parser.add_argument('--output-dir', required=True, type=str, help='Directory for output photos')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f'Not found [directory={input_dir}] with photos!')

    output_dir = Path(args.output_dir)
    if output_dir.exists():
        raise FileExistsError(f'Already exists [directory={output_dir}] with photos!')

    photo_times = parse_photo_times(input_dir)
    photo_times = interpolate_photo_times(photo_times)
    save_photos_with_times(photo_times, output_dir)


if __name__ == '__main__':
    main()
