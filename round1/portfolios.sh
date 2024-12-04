#!/bin/sh
set -x

OUTDIR="output/"
IMAGE_LOCATION=local  # or aws_s3
# point local to the root URL / so that images come straight from http://host.domain/img/
SHARED_PARAMS="\
    --local-root-url /
    --basedir ./img/max_resolution/Portfolio_2024-12/ \
    --image-location "$IMAGE_LOCATION" \
    --html-output templates/lightgallery_or_viewerjs_or_nojs.html $@"

./gen.py $SHARED_PARAMS --custom-css '.__gallery{max-width:960px;}' --order-from-filter --filter-images \
    FEL180,FEL1746,FEL9793,FEL1738,14.52,FEL1709,FEL1835,FEL1817,FEL1834,FEL7638 \
    > $OUTDIR/portfolio.html

echo

./gen.py $SHARED_PARAMS --order-from-filter --filter-images \
    FEL1978,FEL1976,15.14.00,FEL1464,FEL9793 \
    > $OUTDIR/bw_portfolio.html

echo

./gen.py $SHARED_PARAMS --order-from-filter --filter-images \
    _FEL0017,_FEL1189,_FEL1350,_FEL1356,_FEL1513,_FEL6640,_FEL7134,_FEL7483,_FEL7638,_FEL8017,_FEL9793,_FEL9888,_FEL9990_1,_FEL9994 \
    > $OUTDIR/landscape_portfolio.html

echo

./gen.py $SHARED_PARAMS --order-from-filter --filter-images \
    _FEL5295_piloto_alerto,_FEL5326,_FEL6710,_FEL7798 \
    > $OUTDIR/wildlife_portfolio.html

echo

./gen.py $SHARED_PARAMS --order-from-filter --filter-images \
    _FEL1513,_FEL6640,_FEL7134,_FEL7483 \
    > $OUTDIR/lowlight_portfolio.html

echo

# All images in a random order
./gen.py $SHARED_PARAMS --shuffled-order --random-seed 42 > $OUTDIR/joined_portfolio.html
