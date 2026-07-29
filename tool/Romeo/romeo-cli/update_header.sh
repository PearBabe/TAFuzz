#!/bin/bash

for file in *
do
    cat $file | sed 's/2014-2024/2014-2024/g' > $file.tmp
    mv $file.tmp $file
done

