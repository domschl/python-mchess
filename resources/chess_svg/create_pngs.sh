#!/bin/zsh
# Uses ImageMagick convert

DEST_SIZE=60
DENSITY=128

convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_bdt45.svg ../../mchess/resources/pieces/bb"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_blt45.svg ../../mchess/resources/pieces/wb"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_kdt45.svg ../../mchess/resources/pieces/bk"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_klt45.svg ../../mchess/resources/pieces/wk"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_ndt45.svg ../../mchess/resources/pieces/bn"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_nlt45.svg ../../mchess/resources/pieces/wn"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_pdt45.svg ../../mchess/resources/pieces/bp"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_plt45.svg ../../mchess/resources/pieces/wp"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_qdt45.svg ../../mchess/resources/pieces/bq"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_qlt45.svg ../../mchess/resources/pieces/wq"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_rdt45.svg ../../mchess/resources/pieces/br"$DEST_SIZE".png
convert -background transparent -density "$DENSITY" -resize "$DEST_SIZE"x Chess_rlt45.svg ../../mchess/resources/pieces/wr"$DEST_SIZE".png
cp license.md ../../mchess/resources/pieces/


