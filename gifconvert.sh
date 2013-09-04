#!/bin/bash
# Converts .jpg images to .gif for HTML plots
cd ~/Documents/HeliPlot/OutputPlots
for i in *.jpg; do
	convert $i ${i%.jpg}.gif
done
