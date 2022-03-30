#!/bin/bash

action=$1
if ! [ "$action" == "move" ] && ! [ "$action" == "copy" ]; then
    echo "arg should be 'move' or 'copy'"
    exit 1;
fi

for file in `ls ./*.{png,jpeg,jpg,JPG}`; do
    if [ -d "$file" ]; then
	continue
    fi
    eog "$file"
    echo "...?"
    read
    if [ "$action" == "move" ]; then
	if [ "$REPLY" == "" ]; then
	    if [ "$last" != "" ] && [ -d $last ]; then  # move it to same dir as last one
		mv -v $file $last/
	    else
		echo "skipping"
		continue
	    fi
	elif [ "$REPLY" == "rm" ]; then
	    rm -v "$file"
	else
	    mkdir -p $REPLY
	    mv -v $file $REPLY/
	    last=$REPLY
	fi
    elif [ "$action" == "copy" ]; then
	if [ "$REPLY" == "" ]; then
	    continue
	else
	    mkdir -p $REPLY
	    cp -v $file $REPLY/
	fi
    fi	
done
