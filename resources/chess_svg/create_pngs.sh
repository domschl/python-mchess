#!/bin/zsh
# Uses ImageMagick convert

DEST_SIZE=512
echo ""$DEST_SIZE" factor"

convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_bdt45.svg ../../mchess/resources/pieces/bb.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_blt45.svg ../../mchess/resources/pieces/wb.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_kdt45.svg ../../mchess/resources/pieces/bk.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_klt45.svg ../../mchess/resources/pieces/wk.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_ndt45.svg ../../mchess/resources/pieces/bn.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_nlt45.svg ../../mchess/resources/pieces/wn.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_pdt45.svg ../../mchess/resources/pieces/bp.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_plt45.svg ../../mchess/resources/pieces/wp.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_qdt45.svg ../../mchess/resources/pieces/bq.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_qlt45.svg ../../mchess/resources/pieces/wq.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_rdt45.svg ../../mchess/resources/pieces/br.png
convert  -background none -density "$DEST_SIZE" -resize "$DEST_SIZE"x Chess_rlt45.svg ../../mchess/resources/pieces/wr.png
cp license.md ../../mchess/resources/pieces/


