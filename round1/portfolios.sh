#!/bin/sh
set -x

# OUTDIR should end in one forward slash
OUTDIR="$(realpath --relative-to="$PWD" "${OUTDIR:-output}")"

mkdir -p "$OUTDIR"

IMAGE_LOCATION=local  # or aws_s3
# point local to the root URL / so that images come straight from http://host.domain/img/
SHARED_PARAMS="\
    --overwrite-artist Felina \
    --local-root-url / \
    --basedir ./img/max_resolution/Portfolio_2024-12/ \
    --image-location "$IMAGE_LOCATION" \
    --html-template templates/lightgallery_or_viewerjs_or_nojs.html $@"

./gen.py $SHARED_PARAMS --custom-css '.__gallery{max-width:960px;}' --order-from-filter --filter-images \
    FEL180,FEL1746,FEL9793,FEL1738,14.52,FEL1709,FEL1817,FEL1835,FEL1834 \
    --html-output $OUTDIR/index.html

echo

./gen.py $SHARED_PARAMS --order-from-filter --filter-images \
    FEL1978-1,FEL1976-1,15.14.00,FEL1464,FEL1513,FEL1997 \
    --html-output $OUTDIR/bw.html

echo

./gen.py $SHARED_PARAMS --order-from-filter --filter-images \
    _FEL0017,_FEL1189,_FEL1350,_FEL1356,_FEL1513,_FEL6640,_FEL7134,_FEL7483,_FEL7638,_FEL8017,_FEL9793,_FEL9888,_FEL9990_1,_FEL9994 \
    --html-output $OUTDIR/land.html

echo

./gen.py $SHARED_PARAMS --order-from-filter --filter-images \
    _FEL5295_piloto_alerto,_FEL5326,_FEL6710,_FEL7798 \
    --html-output $OUTDIR/life.html

echo

./gen.py $SHARED_PARAMS --order-from-filter --filter-images \
    _FEL1513,_FEL6640,_FEL7134,_FEL7483 \
    --html-output $OUTDIR/low.html

echo

./gen.py $SHARED_PARAMS --order-from-filter --filter-images \
    FEL0970,FEL1011 \
    --html-output $OUTDIR/minimal.html

echo

./gen.py $SHARED_PARAMS --order-from-filter --custom-css '.__gallery{max-width:960px;}' --filter-images \
    FEL9888,FEL7483,FEL1189,FEL6640,FEL7638,FEL0017,FEL6710,FEL8017 \
    --html-output $OUTDIR/up.html

echo

# All images in a random order
./gen.py $SHARED_PARAMS --shuffled-order --random-seed 42 > $OUTDIR/all.html
