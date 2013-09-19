#!/usr/bin/python
import os, re, string

# ----------------------------------------------------------
# Script reads in stationNames.txt file and prestation.cfg 
# and creates a station.cfg file for HeliPlot.py 
# ----------------------------------------------------------

class readStations(object):
	def __init__(self):
		# -------------------------------------------------------
		# Open and read list of stations
		# selected station will be put into cwb.cfg
		# -------------------------------------------------------
		self.stations = []	# list of stations
		self.stationlist = []	# list for edited station names
		self.locations = []	# list of locations for each station	
		fin = open('stationNames.txt', 'r')
		count = 0
		for line in fin:
			count = 0	
			line = line.strip()
			for i in range(len(line)):
				if line[i] == ' ':
					count = count + 1
					if count == 2:
						station = line[0:i].strip()
						station = station.replace(" ", "")	
						location = line[i:len(line)].strip()
						self.stations.append(station)	
						self.locations.append(location)	
					elif count > 2:
						break
						
	def storeStations(self):
		# ------------------------
		# Store station names
		# ------------------------
		stationlen = len(self.stations)
		for i in range(stationlen):
			stringlen = len(self.stations[i])
			# Station IDs have a max size of 6, if (size < 6) then pad
			# station ID with (6-size+1) spaces
			if stringlen == 5:	
				#"\t" + self.stationcmt	
				tmpstation = self.stations[i] + "  " + self.channelID + self.locationID0 + "\t" + self.locations[i]
				self.stationlist.append(tmpstation)
			elif stringlen == 6: 
				#"\t" + self.stationcmt	
				tmpstation = self.stations[i] + " " + self.channelID + self.locationID0 + "\t" + self.locations[i]
				self.stationlist.append(tmpstation)
		
	def writeServerVariables(self):
		# ---------------------------
		# Server variables can change
		# ---------------------------
		print "writeServerVariables()"
		self.cfgout = open('station.cfg', 'w')
		cfgout = self.cfgout	
		cfgout.write(self.cfgcmt)
		cfgout.write("\n")
		cfgout.write("# These variables will only change depending on the execution time and server used\n")
		cfgout.write(self.duration + "\t" + self.durationcmt)
		cfgout.write("\n")
		cfgout.write(self.ipaddress + "\t" + self.ipaddresscmt)
		cfgout.write("\n")
		cfgout.write(self.httpport + "\t" + self.httpportcmt)
		cfgout.write("\n\n")
		
	def writeFilterVariables(self):
		# -------------------------------------------------------------------------	
		# Filter design for stations: this will change depending on how the
		# user wants to filter the data and what station they're pulling the data
		# -------------------------------------------------------------------------	
		print "writeFilterVariables()"	
		cfgout = self.cfgout	
		cfgout.write("# Filter Design\n")
		if self.filtertype == "bandpass":
			fl1 = self.bplowerfreq	# lower band freq
			fl3 = self.bpupperfreq	# upper band freq
			cfgout.write(self.filtertype + "\t" + self.filtertypecmt + "\n")
			cfgout.write(fl1 + "\t" + self.bplowerfreqcmt + "\n")
			cfgout.write(fl3 + "\t" + self.bpupperfreqcmt + "\n")
		elif self.filtertype == "lowpass":
			lpfl = self.lpfreq	# corner freq (this value will change depending on data)
			cfgout.write(self.filtertype + "\t" + self.filtertypecmt + "\n")
			cfgout.write(lpfl + "\t" + self.lpfreqcmt + "\n")
		elif self.filtertype == "highpass":
			hpfl = self.hpfreq	# corner freq (this value will change depending on data)
			cfgout.write(self.filtertype + "\t" + self.filtertypecmt + "\n")
			cfgout.write(hpfl + "\t" + self.hpfreqcmt + "\n")	
		elif self.filtertype == "notch":
			notchfl = self.notchfreq
			cfgout.write(self.filtertype + "\t" + self.filtertypecmt + "\n")
			cfgout.write(notchfl + "\t" + self.notchfreqcmt + "\n")
		cfgout.write(self.magnification + "\t" + self.magnificationcmt + "\n")
		cfgout.write(self.resx + "\t" + self.resxcmt + "\n")
		cfgout.write(self.resy + "\t" + self.resycmt + "\n")
		cfgout.write(self.pix + "\t" + self.pixcmt + "\n")
		cfgout.write(self.imgformat + "\t" + self.imgformatcmt + "\n")	
		cfgout.write(self.vertrange + "\t" + self.vertrangecmt + "\n\n")

		# Prefilter desgin (bandpass with 4 corner frequencies)
		cfgout.write("# PreFilter Design (4 corner frequencies)\n")
		cfgout.write(self.c1 + "\t" + self.c1cmt + "\n")
		cfgout.write(self.c2 + "\t" + self.c2cmt + "\n")
		cfgout.write(self.c3 + "\t" + self.c3cmt + "\n")
		cfgout.write(self.c4 + "\t" + self.c4cmt + "\n\n")	

	def writePathsStations(self):
		# --------------------------------------------------	
		# Create file paths for SeedFiles and OutputPlots
		# Print station info/location to config file
		# --------------------------------------------------	
		print "writePathsStations()"	
		cfgout = self.cfgout	
		if not os.path.exists(self.seedpath):
			print self.seedpath + " DNE, creating path..."
			os.makedirs(self.seedpath)
		if not os.path.exists(self.plotspath):
			print self.plotspath + " DNE, creating path..."
			os.makedirs(self.plotspath)
		cfgout.write("# Directory paths for seedfiles, plots, responses, etc.\n")
		cfgout.write(self.seedpath + "\t" + self.seedpathcmt + "\n")
		cfgout.write(self.plotspath + "\t" + self.plotspathcmt + "\n")
		cfgout.write(self.cwbquery + "\t" + self.cwbquerycmt + "\n")
		cfgout.write(self.resppath + "\t" + self.resppathcmt + "\n\n")

		# Print station info to config file
		cfgout.write(self.stationcmt + "\n")	
		for i in range(len(self.stationlist)):
			cfgout.write(self.stationlist[i] + "\n")

	def prestationInfo(self):
		# -------------------------------------------------------
		# Pull desired station (will this be a user input?)
		# If not then we can loop through all stations and print
		# them to a config file (cwb.cfg)
		# -------------------------------------------------------
		# How will we know the start times for each station? 
		# IU AFI:	start = 20:15 08/07/13
		# CU CIP: 	start = 20:07 08/07/13
		# IU FUNA:	start = 20:15 08/07/13 
		# ------------------------------------------------------

		# Read in data from prestation.cfg this file contains
		# channel/location, datetime/duration, etc.
		fin = open('prestation.cfg', 'r')
		for line in fin:
			if (line[0] != '#'):
				if line != '\n':
					newline = re.split('=', line)
					if "channel" in newline[0]:
						self.channelID = newline[1].strip()
					elif "locationID0" in newline[0]:
						self.locationID0 = newline[1].strip()
					elif "locationID1" in newline[0]:
						self.locationID1 = newline[1].strip()
					elif "duration" in newline[0]:
						self.duration = newline[1].strip()
					elif "ipaddress" in newline[0]:
						self.ipaddress = newline[1].strip()
					elif "httpport" in newline[0]:
						self.httpport = newline[1].strip()
					elif "filtertype" in newline[0]:
						self.filtertype = newline[1].strip()
					elif "bplower" in newline[0]:
						self.bplowerfreq = newline[1].strip()
					elif "bpupper" in newline[0]:
						self.bpupperfreq = newline[1].strip()
					elif "lpfreq" in newline[0]:
						self.lpfreq = newline[1].strip()
					elif "hpfreq" in newline[0]:
						self.hpfreq = newline[1].strip()
					elif "notchfreq" in newline[0]:
						self.notchfreq = newline[1].strip()
					elif "magnification" in newline[0]:
						self.magnification = newline[1].strip()
					elif "resx" in newline[0]:
						self.resx = newline[1].strip()
					elif "resy" in newline[0]:
						self.resy = newline[1].strip()
					elif "pix" in newline[0]:
						self.pix = newline[1].strip()
					elif "imgformat" in newline[0]:
						self.imgformat = newline[1].strip()
					elif "vert" in newline[0]:
						self.vertrange = newline[1].strip()
					elif "prefiltf1" in newline[0]:
						self.c1 = newline[1].strip()
					elif "prefiltf2" in newline[0]:
						self.c2 = newline[1].strip()
					elif "prefiltf3" in newline[0]:
						self.c3 = newline[1].strip()
					elif "prefiltf4" in newline[0]:
						self.c4 = newline[1].strip()
					elif "cwbquery" in newline[0]:
						self.cwbquery = newline[1].strip()
					elif "resppath" in newline[0]:
						self.resppath = newline[1].strip()
					elif "seedpath" in newline[0]:
						self.seedpath = newline[1].strip()
					elif "plotspath" in newline[0]:
						self.plotspath = newline[1].strip()

		# Comments associated with each variable
		self.stationcmt = "# Station Data"
		self.durationcmt = "# duration"
		self.ipaddresscmt = "# ipaddress of local ANMO server"
		self.httpportcmt = "# httpport number of local CWB Server (aslcwb.cr.usgs.gov) this will change accordingly to find open ports for ip addr run: nmap <ipaddr>"
		self.filtertypecmt = "# filter type"
		self.c1cmt = "# prefilt c1"
		self.c2cmt = "# prefilt c2"
		self.c3cmt = "# prefilt c3"
		self.c4cmt = "# prefilt c4"
		self.bplowerfreqcmt = "# bplower freq"
		self.bpupperfreqcmt = "# bpupper freq"
		self.lpfreqcmt = "# lp freq"
		self.hpfreqcmt = "# hp freq"
		self.notchfreqcmt = "# notch freq"
		self.magnificationcmt = "# magnification factor"
		self.resxcmt = "# xresolution"
		self.resycmt = "# yresolution"
		self.pixcmt = "# pixels per inch"
		self.imgformatcmt = "# image format (*.jpg, *.png, etc.)"	
		self.vertrangecmt = "# vertical scaling range"
		self.cwbquerycmt = "# cwbquery jar file"
		self.resppathcmt = "# responses path"
		self.seedpathcmt = "# seed path"
		self.plotspathcmt = "# plots path"
		self.cfgcmt = "# Config file is populated by readStations.py\n# station info will be read from station list\n# execution times will depend on cronjob or an\n# external time file that lists times for each station\n# ---------------------------------------------------\n# These values should not be user input when running a cronjob\n# f1 = bandpass lowerbound\n# f3 = bandpass upperbound\n# mag = magnification factor\n# -------------------------------------------------\n"

# -----------------------------
# Main program 
# -----------------------------
if __name__ == '__main__':
	stations = readStations()
	stations.prestationInfo()
	stations.storeStations()	
	stations.writeServerVariables()
	stations.writeFilterVariables()
	stations.writePathsStations()	
