ls /media/data2/song/newdownload | sort -R |tail -500 |while read file; do
  echo /media/data2/song/newdownload/$file /media/data2/song/random_500/$file

  size=$(du -s /media/data2/song/newdownload/$file | cut -f1)
  maxsize=5000
  if [ "$size" -lt "$maxsize" ];
  then
    echo $size
    cp -rf /media/data2/song/newdownload/$file /media/data2/song/random_500/$file
  fi
done
