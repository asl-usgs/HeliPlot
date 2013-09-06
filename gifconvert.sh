#!/bin/bash
# Converts .jpg images to .gif for HTML plots
cd ~/Documents/HeliPlot/OutputPlots
for i in *.jpg; do
	convert -rotate 0 -crop 0x0 -density 90 $i ${i%.jpg}.pnm
	ppmtogif ${i%.jpg}.pnm > ${i%.jpg}.gif
done
