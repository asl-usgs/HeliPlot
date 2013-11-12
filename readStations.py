#!/usr/bin/env python
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
		self.skipstations = []	# list of network/stations with length > 6	
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
				# Channel/location IDs for station exceptions	
				if self.channelexc.has_key(self.stations[i]) == 1:
					channelID = self.channelexc[self.stations[i]]
				else:
					channelID = self.channelID
				if self.locationexc.has_key(self.stations[i]) == 1:
					locationID = self.locationexc[self.stations[i]]
				else:
					locationID = self.locationID
				tmpstation = self.stations[i] + "  " + channelID + locationID + "\t" + self.locations[i]
				self.stationlist.append(tmpstation)
			elif stringlen == 6: 
				# Channel/location IDs for station exceptions	
				if self.channelexc.has_key(self.stations[i]) == 1:
					channelID = self.channelexc[self.stations[i]]
				else:
					channelID = self.channelID
				if self.locationexc.has_key(self.stations[i]) == 1:
					locationID = self.locationexc[self.stations[i]]
				else:
					locationID = self.locationID
				tmpstation = self.stations[i] + " " + channelID + locationID + "\t" + self.locations[i]
				self.stationlist.append(tmpstation)
			else:
				self.skipstations.append(self.stations[i])
	
	def writeDefaultVariables(self):
		# ---------------------------
		# Server variables can change
		# ---------------------------
		print "writeDefaultVariables()"
		self.cfgout = open('station.cfg', 'w')
		cfgout = self.cfgout	
		cfgout.write(self.cfgcmt)
		cfgout.write("\n")
		cfgout.write("# Default variables\n")
		cfgout.write(self.duration + "\t" + self.durationcmt + "\n")
		cfgout.write(self.ipaddress + "\t" + self.ipaddresscmt + "\n")
		cfgout.write(self.httpport + "\t" + self.httpportcmt + "\n")
		cfgout.write(self.magnification_default + "\t" + self.magnification_defaultcmt + "\n")
		cfgout.write(self.resx + "\t" + self.resxcmt + "\n")
		cfgout.write(self.resy + "\t" + self.resycmt + "\n")
		cfgout.write(self.pix + "\t" + self.pixcmt + "\n")
		cfgout.write(self.imgformat + "\t" + self.imgformatcmt + "\n")	
		cfgout.write(self.vertrange + "\t" + self.vertrangecmt + "\n\n")
	
	def writePaths(self):
		# --------------------------------------------------	
		# Create file paths for SeedFiles and OutputPlots
		# Print station info/location to config file
		# --------------------------------------------------	
		print "writePaths()"	
		cfgout = self.cfgout	
		if not os.path.exists(self.seedpath):
			print self.seedpath + " DNE, creating path..."
			os.makedirs(self.seedpath)
		if not os.path.exists(self.plotspath):
			print self.plotspath + " DNE, creating path..."
			os.makedirs(self.plotspath)
		if not os.path.exists(self.helihtmlpath):
			print self.helihtmlpath + " DNE, creating path..."
			os.makedirs(self.helihtmlpath)
		cfgout.write("# Directory paths for seedfiles, plots, responses, etc.\n")
		cfgout.write(self.seedpath + "\t" + self.seedpathcmt + "\n")
		cfgout.write(self.plotspath + "\t" + self.plotspathcmt + "\n")
		cfgout.write(self.helihtmlpath + "\t" + self.helihtmlpathcmt + "\n")	
		cfgout.write(self.cwbquery + "\t" + self.cwbquerycmt + "\n")
		cfgout.write(self.resppath + "\t" + self.resppathcmt + "\n\n")
		
	def writeFilterVariables(self):
		# -------------------------------------------------------------------------	
		# Filter design for stations: this will change depending on how the
		# user wants to filter the data and what station they're pulling the data
		# -------------------------------------------------------------------------	
		print "writeFilterVariables()"	
		cfgout = self.cfgout	
		cfgout.write("# Filter Designs (unique to channelID)\n")
		cfgout.write("# *NOTE: Filter frequencies will change depending\n")
		cfgout.write("# on the channel being used (i.e. higher/lower freq channels)\n")
		
		# EHZ Filter Design	
		cfgout.write(self.EHZfiltertype + "\t" + self.EHZfiltertypecmt + "\n")
		cfgout.write(self.EHZprefiltf1 + "\t" + self.EHZprefiltf1cmt + "\n")	
		cfgout.write(self.EHZprefiltf2 + "\t" + self.EHZprefiltf2cmt + "\n")	
		cfgout.write(self.EHZprefiltf3 + "\t" + self.EHZprefiltf3cmt + "\n")	
		cfgout.write(self.EHZprefiltf4 + "\t" + self.EHZprefiltf4cmt + "\n")	
		cfgout.write(self.EHZhpfreq + "\t" + self.EHZhpfreqcmt + "\n")
		cfgout.write(self.EHZnotchfreq + "\t" + self.EHZnotchfreqcmt + "\n\n")
		
		# BHZ Filter Design
		cfgout.write(self.BHZfiltertype + "\t" + self.BHZfiltertypecmt + "\n")
		cfgout.write(self.BHZprefiltf1 + "\t" + self.BHZprefiltf1cmt + "\n")
		cfgout.write(self.BHZprefiltf2 + "\t" + self.BHZprefiltf2cmt + "\n")
		cfgout.write(self.BHZprefiltf3 + "\t" + self.BHZprefiltf3cmt + "\n")
		cfgout.write(self.BHZprefiltf4 + "\t" + self.BHZprefiltf4cmt + "\n")
		cfgout.write(self.BHZbplowerfreq + "\t" + self.BHZbplowerfreqcmt + "\n")
		cfgout.write(self.BHZbpupperfreq + "\t" + self.BHZbpupperfreqcmt + "\n\n")

		# LHZ Filter Design
		cfgout.write(self.LHZfiltertype + "\t" + self.LHZfiltertypecmt + "\n")
		cfgout.write(self.LHZprefiltf1 + "\t" + self.LHZprefiltf1cmt + "\n")
		cfgout.write(self.LHZprefiltf2 + "\t" + self.LHZprefiltf2cmt + "\n")
		cfgout.write(self.LHZprefiltf3 + "\t" + self.LHZprefiltf3cmt + "\n")
		cfgout.write(self.LHZprefiltf4 + "\t" + self.LHZprefiltf4cmt + "\n")
		cfgout.write(self.LHZbplowerfreq + "\t" + self.LHZbplowerfreqcmt + "\n")
		cfgout.write(self.LHZbpupperfreq + "\t" + self.LHZbpupperfreqcmt + "\n\n")

		# VHZ Filter Design
		cfgout.write(self.VHZfiltertype + "\t" + self.VHZfiltertypecmt + "\n")
		cfgout.write(self.VHZprefiltf1 + "\t" + self.VHZprefiltf1cmt + "\n")	
		cfgout.write(self.VHZprefiltf2 + "\t" + self.VHZprefiltf2cmt + "\n")	
		cfgout.write(self.VHZprefiltf3 + "\t" + self.VHZprefiltf3cmt + "\n")	
		cfgout.write(self.VHZprefiltf4 + "\t" + self.VHZprefiltf4cmt + "\n")	
		cfgout.write(self.VHZlpfreq + "\t" + self.VHZlpfreqcmt + "\n\n")
		
		# Write magnification exception list for specific stations
		cfgout.write(str(self.magnificationexc) + "\t" + self.magnificationexccmt + "\n\n")

	def writeStations(self):	
		# -----------------------------------	
		# Print station info to config file
		# -----------------------------------	
		print "writeStations()"	
		cfgout = self.cfgout	
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
					if "channelID" in newline[0]:
						self.channelID = newline[1].strip()
					elif "locationID" in newline[0]:
						self.locationID = newline[1].strip()
					elif "duration" in newline[0]:
						self.duration = newline[1].strip()
					elif "ipaddress" in newline[0]:
						self.ipaddress = newline[1].strip()
					elif "httpport" in newline[0]:
						self.httpport = newline[1].strip()
					elif "magnification_default" in newline[0]:
						self.magnification_default = newline[1].strip()
					elif "resx" in newline[0]:
						self.resx = newline[1].strip()
					elif "resy" in newline[0]:
						self.resy = newline[1].strip()
					elif "pix" in newline[0]:
						self.pix = newline[1].strip()
					elif "imgformat" in newline[0]:
						self.imgformat = newline[1].strip()
					elif "vertrange" in newline[0]:
						self.vertrange = newline[1].strip()
					elif "cwbquery" in newline[0]:
						self.cwbquery = newline[1].strip()
					elif "resppath" in newline[0]:
						self.resppath = newline[1].strip()
					elif "seedpath" in newline[0]:
						self.seedpath = newline[1].strip()
					elif "plotspath" in newline[0]:
						self.plotspath = newline[1].strip()
					elif "helihtmlpath" in newline[0]:
						self.helihtmlpath = newline[1].strip()
					elif "EHZfiltertype" in newline[0]:
						self.EHZfiltertype = newline[1].strip()
					elif "EHZprefiltf1" in newline[0]:
						self.EHZprefiltf1 = newline[1].strip()
					elif "EHZprefiltf2" in newline[0]:
						self.EHZprefiltf2 = newline[1].strip()
					elif "EHZprefiltf3" in newline[0]:
						self.EHZprefiltf3 = newline[1].strip()
					elif "EHZprefiltf4" in newline[0]:
						self.EHZprefiltf4 = newline[1].strip()
					elif "EHZhpfreq" in newline[0]:
						self.EHZhpfreq = newline[1].strip()
					elif "EHZnotchfreq" in newline[0]:
						self.EHZnotchfreq = newline[1].strip()
					elif "BHZfiltertype" in newline[0]:
						self.BHZfiltertype = newline[1].strip()
					elif "BHZprefiltf1" in newline[0]:
						self.BHZprefiltf1 = newline[1].strip()
					elif "BHZprefiltf2" in newline[0]:
						self.BHZprefiltf2 = newline[1].strip()
					elif "BHZprefiltf3" in newline[0]:
						self.BHZprefiltf3 = newline[1].strip()
					elif "BHZprefiltf4" in newline[0]:
						self.BHZprefiltf4 = newline[1].strip()
					elif "BHZbplowerfreq" in newline[0]:
						self.BHZbplowerfreq = newline[1].strip()
					elif "BHZbpupperfreq" in newline[0]:
						self.BHZbpupperfreq = newline[1].strip()
					elif "LHZfiltertype" in newline[0]:
						self.LHZfiltertype = newline[1].strip()
					elif "LHZprefiltf1" in newline[0]:
						self.LHZprefiltf1 = newline[1].strip()
					elif "LHZprefiltf2" in newline[0]:
						self.LHZprefiltf2 = newline[1].strip()
					elif "LHZprefiltf3" in newline[0]:
						self.LHZprefiltf3 = newline[1].strip()
					elif "LHZprefiltf4" in newline[0]:
						self.LHZprefiltf4 = newline[1].strip()
					elif "LHZbplowerfreq" in newline[0]:
						self.LHZbplowerfreq = newline[1].strip()
					elif "LHZbpupperfreq" in newline[0]:
						self.LHZbpupperfreq = newline[1].strip()
					elif "VHZfiltertype" in newline[0]:
						self.VHZfiltertype = newline[1].strip()
					elif "VHZprefiltf1" in newline[0]:
						self.VHZprefiltf1 = newline[1].strip()
					elif "VHZprefiltf2" in newline[0]:
						self.VHZprefiltf2 = newline[1].strip()
					elif "VHZprefiltf3" in newline[0]:
						self.VHZprefiltf3 = newline[1].strip()
					elif "VHZprefiltf4" in newline[0]:
						self.VHZprefiltf4 = newline[1].strip()
					elif "VHZlpfreq" in newline[0]:
						self.VHZlpfreq = newline[1].strip()
					elif "channelexc" in newline[0]:
						self.channelexc = newline[1].strip()
					elif "locationexc" in newline[0]:
						self.locationexc = newline[1].strip()
					elif "magnificationexc" in newline[0]:
						self.magnificationexc = newline[1].strip()
		
		# Split/store exception station channels, locations, magnfications
		tmpchan = re.split(',', self.channelexc)
		self.channelexc = {}	
		for i in range(len(tmpchan)):	# split/store channelexc
			tmpexc = re.split(':', tmpchan[i])
			self.channelexc[tmpexc[0].strip()] = tmpexc[1].strip()
		tmploc = re.split(',', self.locationexc)
		self.locationexc = {}
		for i in range(len(tmploc)):	# split/store locationexc
			tmpexc = re.split(':', tmploc[i])
			self.locationexc[tmpexc[0].strip()] = tmpexc[1].strip()
		'''	
		tmpmag = re.split(',', self.magnificationexc)	
		self.magnificationexc = {}
		for i in range(len(tmpmag)):	# split/store magnificationexc
			tmpexc = re.split(':', tmpmag[i])
			self.magnificationexc[tmpexc[0].strip()] = float(tmpexc[1].strip())
		'''

		# Comments associated with each variable
		self.stationcmt = "# Station Data"
		self.durationcmt = "# duration"
		self.ipaddresscmt = "# ipaddress of local ANMO server"
		self.httpportcmt = "# httpport number of local CWB Server (aslcwb.cr.usgs.gov)"
		self.magnification_defaultcmt = "# magnification default"
		self.resxcmt = "# xresolution"
		self.resycmt = "# yresolution"
		self.pixcmt = "# pixels per inch"
		self.imgformatcmt = "# image format (*.jpg, *.png, etc.)"	
		self.vertrangecmt = "# vertical scaling range"
		self.cwbquerycmt = "# cwbquery jar file (system path)"
		self.resppathcmt = "# responses path (system path)"
		self.seedpathcmt = "# temporary seed path (user defined)"
		self.plotspathcmt = "# temporary plots path (user defined)"
		self.helihtmlpathcmt = "# temporary heli html path (user defined)"	
		self.EHZfiltertypecmt = "# EHZ filter type"
		self.EHZprefiltf1cmt = "# EHZ prefilt f1"
		self.EHZprefiltf2cmt = "# EHZ prefilt f2"
		self.EHZprefiltf3cmt = "# EHZ prefilt f3"
		self.EHZprefiltf4cmt = "# EHZ prefilt f4"
		self.EHZnotchfreqcmt = "# EHZ notch frequency"
		self.EHZhpfreqcmt = "# EHZ highpass frequency"
		self.BHZfiltertypecmt = "# BHZ filter type"
		self.BHZprefiltf1cmt = "# BHZ prefilt f1"
		self.BHZprefiltf2cmt = "# BHZ prefilt f2"
		self.BHZprefiltf3cmt = "# BHZ prefilt f3"
		self.BHZprefiltf4cmt = "# BHZ prefilt f4"
		self.BHZbplowerfreqcmt = "# BHZ bplower freq"
		self.BHZbpupperfreqcmt = "# BHZ bpupper freq"
		self.LHZfiltertypecmt = "# LHZ filter type"
		self.LHZprefiltf1cmt = "# LHZ prefilt f1"
		self.LHZprefiltf2cmt = "# LHZ prefilt f2"
		self.LHZprefiltf3cmt = "# LHZ prefilt f3"
		self.LHZprefiltf4cmt = "# LHZ prefilt f4"
		self.LHZbplowerfreqcmt = "# LHZ bplower freq"
		self.LHZbpupperfreqcmt = "# LHZ bpupper freq"
		self.VHZfiltertypecmt = "# VHZ filter type"
		self.VHZprefiltf1cmt = "# VHZ prefilt f1"	
		self.VHZprefiltf2cmt = "# VHZ prefilt f2"	
		self.VHZprefiltf3cmt = "# VHZ prefilt f3"	
		self.VHZprefiltf4cmt = "# VHZ prefilt f4"	
		self.VHZlpfreqcmt = "# VHZ lowpass frequency"
		self.magnificationexccmt = "# magnification exceptions list"	
		self.cfgcmt = "# ---------------------------------------------------\n# Config file is populated by readStations.py\n# station info will be read from station list\n# execution times will depend on cronjob or an\n# external time file that lists times for each station\n# ---------------------------------------------------\n# **NOTE: Each filter design has 4 prefilter corner freqs\n# ---------------------------------------------------\n"

# -----------------------------
# Main program 
# -----------------------------
if __name__ == '__main__':
	stations = readStations()
	stations.prestationInfo()
	stations.storeStations()	
	stations.writeDefaultVariables()
	stations.writePaths()	
	stations.writeFilterVariables()
	stations.writeStations()	
