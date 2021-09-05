## :camera_flash: pretty-photos

Sometimes photos extracted from other devices or elsewhere have names that are difficult to interpret

```
$ ls photos/
...
IMG_2184.JPG
IMG_2184.MOV
IMG_2431.JPEG
...
```

Usually, but not always, those files contain metadata or properties with their creation time.

Script loops through all photos or videos of input dir and renames them according to their creation time.
Often creation time is unknown. In that case, if possible, script will interpolate random time from nearby photos


```
$ python --version
Python 3.7.9
$ pip install -r requirements.txt
$ python order_photos.py --input-dir=photos --output-dir=photos-with-time
```

Output photos with different names are saved into separate directory

```
$ ls photos-with-time/2020/
...
2020-10-27_16:39:16.JPG
2020-12-23_21:15:16.JPEG
2020-12-29_16:36:35.JPEG
...
```

Interpolation will work only for the photos with names `IMG_<number>`, that is common prefix for the files retrieved from
iDevices. Prefix and other parameters can be changed in code.