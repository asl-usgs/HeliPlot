#!/usr/bin/env python

# ----------------------------------------------------
# Author: Alejandro Gonzales
# Filename: run_heli_24hr.py 
# ----------------------------------------------------
# Purpose: Script takes all output heli plots from 
# HeliPlot.py and inserts them into HTML files for 
# each operable station
# ----------------------------------------------------
# Methods (keyword search):
#	* gifConvert()	- Not currently used	
#	* readImages()
#	* heliHTML()	
# ----------------------------------------------------
import os, sys, re, glob, string, subprocess
from datetime import datetime, timedelta

class run_heli_24hr(object):
	def __init__(self):
		# ----------------------------------------------
		# Open and read prestation.cfg for heliplots,
		# stationnames, etc.
		# ----------------------------------------------
		finconfig = open('prestation.cfg', 'r')
		for line in finconfig:
			if(line[0] != '#'):
				if line != '\n':
					newline = re.split('=', line)
					if "plotspath" in newline[0]:
						self.plotspath = str(newline[1].strip())	
					elif "stationnames" in newline[0]:
						self.stationnames = str(newline[1].strip())
					elif "gifconvert" in newline[0]:
						self.gifconvert = str(newline[1].strip())
					elif "nodata" in newline[0]:
						self.nodata = str(newline[1].strip())
					elif "helihtml" in newline[0]:
						self.helihtml = str(newline[1].strip())
	
		print "\nOutput plots path: " + str(self.plotspath) 
		print "Heli plots html path: " + str(self.helihtml)

		# ----------------------------------------------
		# Open and read list of stations/locations
		# ----------------------------------------------
		self.home = os.getcwd()		# current home directory ../HeliPlot	
		self.stations = []		# list of stations
		self.locations = {}		# dict for station locations (arranged by station)
		self.gifstations = []		# list of stations from OutputPlots	
		self.heliplots = {}		# dict of heliplots for each station	
		self.missingstations = []	# missing stations from HeliPlots output

		fin = open(self.stationnames, 'r')
		count = 0
		for line in fin:
			count = 0
			line = line.strip()
			for i in range(len(line)):
				if line[i] == ' ':
					count = count + 1
					if count == 2:
						station = line[0:i].strip()
						tmpst = re.split(' ', station)
						station = tmpst[1].strip()
						location = line[i:len(line)].strip()
						self.stations.append(station)
						self.locations[station] = location	
					elif count > 2:
						break

	def gifConvert(self):
		# --------------------------------------------------------
		# Converts .jpg files produced by HeliPlot to .gif files
		# to be used for the LISS HTML. 	
		# --------------------------------------------------------
		print "\nConverting images from .jpg to .gif..."	
		filelist = sorted(os.listdir(self.plotspath))
		filelen = len(filelist)	
		JPGFLAG = False	
		if filelen != 0:
			for i in range(filelen):
				if ".jpg" in filelist[i]:
					JPGFLAG = True	
					try:
						os.chdir(self.plotspath)	
						process = subprocess.Popen([self.gifconvert], stderr=subprocess.PIPE, shell=True)
						(out, err) = process.communicate()
					except Exception as e:
						print "*****Exception found = " + str(e)
				else:
					JPGFLAG = False 
			if not JPGFLAG:
				print "****ALL *.JPG CONVERTED to *.GIF****\n"
		else:
			print "****NO FILES PRESENT IN HELIPLOTS DIR****\n"
	
	def readImages(self):
		# ---------------------------------------
		# Read in images from HeliPlots	
		# ---------------------------------------
		print "Reading in images from OutputPlots/..."	
		filelist = sorted(os.listdir(self.plotspath))
		filelen = len(filelist)
		if filelen != 0:
			for i in range(filelen):
				tmp = re.split('\\.', filelist[i])
				self.gifstations.append(tmp[1].strip())		# only get locations for stations that exist for HeliPlots
				self.heliplots[tmp[1].strip()] = filelist[i]	# corresponding HeliPlot for each station

		for i in range(len(self.stations)):
			if not self.stations[i] in self.gifstations:
				self.missingstations.append(self.stations[i])	# store missing stations
		print "****Missing station data****"	
		'''for s in self.missingstations:
			print s'''
	
	def heliHTML(self):
		# --------------------------------------------------
		# Create HTML files for each station HeliPlot
		# contained in the self.gifstations list, the 
		# locations associated with each of these stations
		# is contained within the self.locations dict
		# --------------------------------------------------
		print "\nCreating html files for each heliplot image..."	
		# Get MST/GMT date/times from system 
		os.chdir(self.helihtml)	
		htmlfiles = glob.glob(self.helihtml+"*")
		for f in htmlfiles:
			os.remove(f)	# remove temp html files from HeliHTML dir
		try:	
				
			procMST = subprocess.Popen(["date '+%a %m/%d/%y %H:%M %Z'"], stdout=subprocess.PIPE, shell=True)	
			procGMT = subprocess.Popen(["date -u '+%a %m/%d/%y %H:%M %Z'"], stdout=subprocess.PIPE, shell=True)	
			(dateMST, errMST) = procMST.communicate()
			(dateGMT, errGMT) = procGMT.communicate()	
		except Exception as e:
			print "*****Exception found = " + str(e)
		
		# Loop through all stations, if station is missing in
		# HeliPlots we will replace that image with NODATA.gif
		dateMST = dateMST.strip()
		dateGMT = dateGMT.strip()
		width = "1280"
		height = "700"
		align = "center"	
		NODATAFLG = False	
		for i in range(len(self.stations)):
			station = self.stations[i]
			location = self.locations[station]
			htmlname = station + "_24hr.html"
			if station in self.missingstations:
				NODATAFLG = True	
				image = self.nodata
			else:
				NODATAFLG = False	
				image = self.heliplots[station]	
			html = open(htmlname, 'w')	
			html.write("<!DOCTYPE html>\n")
			html.write("<html>\n")
			html.write("\t<head>\n")
			html.write("\t\t<title>ASL DCC " + station + " TELEMETRY DATA</title>\n")
			html.write("\t</head>\n")
			html.write("\t<body>\n")
			html.write("\t\t<h2><CENTER>Data from station " + station + " (" + location + ")</CENTER></h2>\n")
			html.write("\t\t<h3><CENTER>last updated at</CENTER></h3>\n")
			html.write("\t\t<h3><CENTER>" + dateMST + " (" + dateGMT + ")</CENTER></h3>\n")
			if NODATAFLG:
				html.write("\t\t<CENTER><img src=" + '"' + image + '"' + " width=" + '"' + width + '"' + " height=" + '"' + height + '"' + "></CENTER>\n") 
			else:	
				html.write("\t\t<CENTER><img src=" + '"' + self.plotspath + image + '"' + " width=" + '"' + width + '"' + " height=" + '"' + height + '"' + "></CENTER>\n") 
			html.write("\t\t<p align=" + '"' + align + '"' + ">\n")
			html.write("\t</body>\n")
			html.write("</html>")

if __name__ == '__main__':
	heli = run_heli_24hr()
	#heli.gifConvert()	
	heli.readImages()
	heli.heliHTML()	
