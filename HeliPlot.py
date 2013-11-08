#!/usr/bin/env python
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.stream import read
from obspy.signal.invsim import evalresp
from multiprocessing import Manager, Value
import numpy as np
import functools
import logging
import multiprocessing
import warnings, glob, re, os, sys, string, subprocess
from datetime import datetime, timedelta
import signal

# -----------------------------------------------------------------
# Script reads in configurations from station.cfg and queries
# stations, station data is then deconvolved, filtered, 
# magnified and plotted. Outputs will be station data images in
# a jpg format. When script is finished processing, run
# run_heli_24hr.py to generate HTML files for each station
# -----------------------------------------------------------------

class KeyboardInterruptError(Exception): pass	# raises KeyboardInterrupts for multiprocessing methods

# Unpack self from arguments and call method cwbQuery()
def unwrap_self_cwbQuery(args, **kwargs):
	return HeliPlot.cwbQuery(*args, **kwargs)

# Unpack self from arguments and call method freqDeconvFilter() 
def unwrap_self_freqDeconvFilter(args, **kwargs):
	return HeliPlot.freqDeconvFilter(*args, **kwargs)

# Unpack self from args and call method plotVelocity()
def unwrap_self_plotVelocity(args, **kwargs):
	return HeliPlot.plotVelocity(*args, **kwargs)

# ---------------------------------------------------------
# HeliPlot() uses CWBQuery to query station streams,
# streams are then filtered and plotted using ObsPy
# ---------------------------------------------------------
class HeliPlot(object):
	def cwbQuery(self, station):
		# ------------------------------------------------
		# Pull specific station seed file using CWBQuery
		# ------------------------------------------------
		try:
			proc = subprocess.Popen(["java -jar  " + self.cwbquery + " -s " + '"'+station+'"' + " -b " + '"'+self.datetimeQuery+'"' + " -d " + '"'+str(self.duration)+'"' + " -t dcc512 -o " + self.seedpath+"%N_%y_%j -h " + '"'+self.ipaddress+'"'], stdout=subprocess.PIPE, shell=True)
			(out, err) = proc.communicate()
			print out	
		except KeyboardInterrupt:
			print "KeyboardInterrupt: terminate cwbQuery() workers"	
			raise KeyboardInterruptError()	
		except Exception as e:
			print "*****Exception found = " + str(e)

	def parallelcwbQuery(self):
		# --------------------------------------------------
		# Initialize all variables needed to run cwbQuery()
		# --------------------------------------------------
		self.home = os.getcwd()
		files = glob.glob(self.seedpath+"*")
		for f in files:
			os.remove(f)	# remove tmp seed files from SeedFiles dir
		stationlen = len(self.stationinfo)

		# -----------------------------------------------
		# Create multiprocessing pools to run multiple 
		# instances of cwbQuery()
		# -----------------------------------------------
		cpu_count = multiprocessing.cpu_count()
		PROCESSES = cpu_count
		pool = multiprocessing.Pool(PROCESSES) 
		try:
			print "Starting Pool map cwbQuery()"	
			pool.map(unwrap_self_cwbQuery, zip([self]*stationlen, self.stationinfo))
			
			pool.close()
			pool.join()	
			pool.terminate()	
			pool.join()	
		except KeyboardInterrupt:
			print "Caught KeyboardInterrupt: terminating cwbQuery() workers"
			pool.terminate()
			pool.join()	
			sys.exit(0)	
			print "Pool cwbQuery() is terminated"	
		except Exception, e:
			print "Got exception: %r, terminating the Pool" % (e,)
			pool.terminate()
			pool.join()	
			sys.exit(0)
			print "Pool cwbQuery() is terminated"

	def pullTraces(self):
		# ------------------------------------------------
		# Open seed files from cwbQuery and pull trace
		# stats from the data stream
		# ------------------------------------------------
		os.chdir(self.seedpath)
		filelist = sorted(os.listdir(self.seedpath), key=os.path.getctime)
		self.filelist = filelist	
		filelen = len(filelist)
		stream = [0 for x in range(filelen)]	# multidim streams list, streams for each file contain multiple traces so streams = [][] where the second entry denotes the traces index
		i = filelen - 1
		while i >= 0:
			try:
				stream[i] = read(filelist[i])	# read MSEED files from query
			except Exception as e:
				print "*****Exception found = " + str(e)
			i = i - 1
		
		streamlen = len(stream)	# number of streams (i.e. stream files)
		self.streamlen = streamlen	
		trace = {}	# dict of traces for each stream
		for i in range(streamlen):
			strsel = stream[i]	# selected stream
			tracelen = len(strsel)	# number of traces in stream
			index = str(i)
			if tracelen == 1:	# single trace stream
				trace[index] = strsel[0]	# trace 0 in stream[i]
			elif tracelen > 1:	# multiple trace stream
				trace[index] = []	# list in dict
				for j in range(tracelen):
					trace[index].append(strsel[j])

		# Loop through stream traces, if trace has sample rate = 0.0Hz
		# => NFFT = 0, then this trace will be removed
		for i in range(streamlen):
			index = str(i)
			tracelen = stream[i].count()
			if tracelen == 1:
				if trace[index].stats['sampling_rate'] == 0.0:
					stream[i].remove(trace[index])
			elif tracelen > 1:
				for j in range(tracelen):
					if trace[index][j].stats['sampling_rate'] == 0.0:
						stream[i].remove(trace[index][j])
		self.stream = stream

	def freqResponse(self):
		# -----------------------------------------------------------
		# Pull frequency response for station and run a simulation
		# to deconvolve signal, after deconvolution filter signal
		# -----------------------------------------------------------
		networkID = []
		stationID = []
		locationID = []
		channelID = []
		# Need stations listed in SeedFiles directory
		for i in range(self.streamlen):
			tmpstation = self.filelist[i]	
			stationindex = tmpstation.index('_')
			networkID.append(str(tmpstation[0:2]))
			stationID.append(str(tmpstation[2:stationindex]))
			locationindex = len(tmpstation)-11
			channelindex = len(tmpstation)-14
			locationID.append(str(tmpstation[locationindex:locationindex+2]))
			channelID.append(str(tmpstation[channelindex:channelindex+3]))
		self.networkID = networkID
		self.stationID = stationID
		self.locationID = locationID
		self.channelID = channelID

		# -------------------------------------------------------------------
		# Loop through stations and get frequency responses for each stream
		# -------------------------------------------------------------------
		stationName = []	# station names for output plots
		self.resp = []		# station frequency responses for deconvolution	
		for i in range(self.streamlen):
			# NOTE: For aslres01 frequency responses are 
			# contained in /APPS/metadata/RESPS/
			resfilename = "RESP."+networkID[i]+"."+stationID[i]+"."+locationID[i]+"."+channelID[i]	# response filename
			tmpname = re.split('RESP.', resfilename) 	
			stationName.append(tmpname[1].strip())	
			self.stationName = stationName	# store station names	
			
			os.chdir(self.resppath)	# cd into response directory
			resp = {'filename': resfilename, 'date': self.datetimeUTC, 'units': 'VEL'}	# frequency response of data stream in terms of velocity
			self.resp.append(resp)	
			print "stream[%d]" % i
			print "number of traces = " + str(len(self.stream[i]))
			print "datetimeUTC = " + str(self.datetimeUTC)
			print "resfilename = " + str(resfilename)
			print "\n"

	def freqDeconvFilter(self, stream, response):
		# Make sure stream and response names match	
		tmpstr = re.split("\\.", stream[0].getId())
		namestr = tmpstr[1].strip()
		nameloc = tmpstr[2].strip()	
		namechan = tmpstr[3].strip()	
		nameres = response['filename'].strip() 
		if namechan == "EHZ":
			filtertype = self.EHZfiltertype
			c1 = self.EHZprefiltf1
			c2 = self.EHZprefiltf2
			c3 = self.EHZprefiltf3
			c4 = self.EHZprefiltf4
			hpfreq = self.EHZhpfreq
			notchfreq = self.EHZnotchfreq	# notch filter will be implemented later
		elif namechan == "BHZ":
			filtertype = self.BHZfiltertype
			c1 = self.BHZprefiltf1
			c2 = self.BHZprefiltf2
			c3 = self.BHZprefiltf3
			c4 = self.BHZprefiltf4
			bplowerfreq = self.BHZbplowerfreq	
			bpupperfreq = self.BHZbpupperfreq	
		elif namechan == "LHZ":
			filtertype = self.LHZfiltertype
			c1 = self.LHZprefiltf1
			c2 = self.LHZprefiltf2
			c3 = self.LHZprefiltf3
			c4 = self.LHZprefiltf4
			bplowerfreq = self.LHZbplowerfreq
			bpupperfreq = self.LHZbpupperfreq	
		elif namechan == "VHZ":
			filtertype = self.VHZfiltertype
			c1 = self.VHZprefiltf1
			c2 = self.VHZprefiltf2
			c3 = self.VHZprefiltf3
			c4 = self.VHZprefiltf4
			lpfreq = self.VHZlpfreq
			
		try:	
			print "Filter stream " + namestr + " and response " + nameres 
			print namechan + " filtertype = " + str(filtertype) 
			print "c1 = " + str(c1)
			print "c2 = " + str(c2)
			print "c3 = " + str(c3)
			print "c4 = " + str(c4) 
			
			# Deconvolution (remove sensitivity)
			sensitivity = "Sensitivity:"	# pull sensitivity from RESP file
			grepSensitivity = "grep " + '"' + sensitivity + '"' + " " + nameres + " | tail -1"
			proc = subprocess.Popen([grepSensitivity], stdout=subprocess.PIPE, shell=True)
			(out, err) = proc.communicate()
			tmps = out.strip()
			tmps = re.split(':', tmps)
			s = float(tmps[1].strip())
			print "sensitivity = " + str(s) 
			# divide data by sensitivity	
			#stream.simulate(paz_remove=None, pre_filt=(c1, c2, c3, c4), seedresp=response, taper='True')	# deconvolution (this will be a flag for the user)
			stream[0].data = stream[0].data / s	# remove sensitivity gain from stream data
				
			if filtertype == "bandpass":
				print "Filtering stream (bandpass)"
				print "bp lower freq = " + str(bplowerfreq) 
				print "bp upper freq = " + str(bpupperfreq) + "\n" 
				stream.filter(filtertype, freqmin=bplowerfreq, freqmax=bpupperfreq, corners=2)	# bandpass filter design
			elif filtertype == "lowpass":
				print "Filtering stream (lowpass)"
				print "lp freq = " + str(lpfreq) + "\n"
				stream.filter(filtertype, freq=lpfreq, corners=1)	# lowpass filter design
			elif filtertype == "highpass":
				print "Filtering stream (highpass)"
				print "hpfreq = " + str(hpfreq) + "\n"
				stream.filter(filtertype, freq=hpfreq, corners=1)	# highpass filter design	

			return stream 
		except KeyboardInterrupt:
			print "KeyboardInterrupt: terminate freqDeconvFilter() workers"
			raise KeyboardInterruptError()
		except Exception as e:
			return "*****Exception found = " + str(e)
	
	def parallelfreqDeconvFilter(self):
		# -------------------------------------------------------------------
		# Simulation/filter for deconvolution
		# NOTE: Filter will be chosen by user, this includes filter 
		# coefficients and frequency ranges. Currently all stations run the
		# same filter design (i.e. bandpass), this will change depending on 
		# the network and data extracted from each station, the higher freq
		# signals will need to use a notch or high freq filter
		# -------------------------------------------------------------------
		# Pre-filter bandpass corner frequencies eliminate end frequency
		# spikes (i.e. H(t) = F(t)/G(t), G(t) != 0)
		# -------------------------------------------------------------------
		for i in range(self.streamlen):	
			self.stream[i].merge(method=1, fill_value='interpolate', interpolation_samples=100)	# merge traces to eliminate small data lengths, method 0 => no overlap of traces (i.e. overwriting of previous trace data)

		# Deconvolution/Prefilter	
		# Initialize multiprocessing pools
		cpu_count = multiprocessing.cpu_count()
		PROCESSES = cpu_count
		pool = multiprocessing.Pool(PROCESSES)
		try:
			print "Starting Pool map freqDeconvFilter()\n"	
			flt_streams = pool.map(unwrap_self_freqDeconvFilter, zip([self]*self.streamlen, self.stream, self.resp))	
			
			pool.close()
			pool.join()	
			pool.terminate()	
			pool.join()
			
			self.flt_streams = flt_streams
		except KeyboardInterrupt:
			print "Caught KeyboardInterrupt: terminating freqDeconvFilter() workers"
			pool.terminate()
			pool.join()	
			sys.exit(0)	
			print "Pool freqDeconvFilter() is terminated"
		except Exception, e:
			print "Got exception: %r, terminating the Pool" % (e,)
			pool.terminate()
			pool.join()	
			sys.exit(0)	
			print "Pool freqDeconvFilter() is terminated"

	def magnifyData(self):
		# ----------------------------------------
		# Magnify streams by specified 
		# magnification factor 
		# ----------------------------------------
		streams = self.flt_streams	
		streamlen = len(streams)
		self.magnification = {}	# dict containing magnifications for each station	
		for i in range(streamlen):
			tracelen = streams[i].count()	
			if tracelen == 1:
				tr = streams[i][0]	# single trace within stream
				data = tr.data		# data samples from single trace	
				datalen = len(data)	# number of data points within single trace
				tmpId = re.split("\\.", tr.getId())	# stream ID
				networkId = tmpId[0].strip()		# network ID	
				stationId = tmpId[1].strip()		# station ID
				netstationId = networkId + stationId	# network/station ID	
				print "Magnifying stream " + str(tr.getId()) 
				if netstationId in self.magnificationexc:	
					magnification = self.magnificationexc[netstationId]	
				else:
					magnification = self.magnification_default
				print "magnification = " + str(magnification) + "\n"
				self.magnification[streams[i][0].getId()] = magnification	
				streams[i][0].data = streams[i][0].data * magnification 
	
		return streams	
	
	def plotVelocity(self, stream, stationName):
		# --------------------------------------------------------
		# Plot velocity data	
		# --------------------------------------------------------
		#stream.merge(method=1, fill_value='interpolate', interpolation_samples=100)	# for gapped/overlapped data run a linear interpolation with 100 samples
		try:	
			print "Plotting velocity data for station " + str(stationName) + "\n"
			magnification = self.magnification[stream[0].getId()]	# magnification for station[i]
			tmpstr = re.split("\\.", stream[0].getId())
			namechan = tmpstr[3].strip()
			if namechan == "EHZ":
				filtertype = self.EHZfiltertype
			elif namechan == "BHZ":
				filtertype = self.BHZfiltertype
			elif namechan == "LHZ":
				filtertype = self.LHZfiltertype
			elif namechan == "VHZ":
				filtertype = self.VHZfiltertype
			
			stream.plot(type='dayplot', interval=60,
				vertical_scaling_range=self.vertrange,
				right_vertical_lables=False, number_of_ticks=7,
				one_tick_per_line=True, color=['k'],
				show_y_UTC_label=False, size=(self.resx,self.resy),
				dpi=self.pix, title_size=7,
				title=stream[0].getId()+"  "+"Start Date/Time: "+str(self.datetimeQuery)+"  "+"Filter: "+str(filtertype)+"  "+"Vertical Trace Spacing = Ground Vel = 3.33E-4 mm/sec"+"  "+"Magnification = "+str(magnification), outfile=stationName+"."+self.imgformat)

		except KeyboardInterrupt:
			print "KeyboardInterrupt: terminate plotVelocity() workers"
			raise KeyboardInterruptError()
		except Exception as e:
			return "*****Exception found = " + str(e)

	def parallelPlotVelocity(self, streams):	
		# --------------------------------------------------------
		# Plot velocity data	
		# --------------------------------------------------------
		streamlen = len(streams)	
		os.chdir(self.plotspath)
		imgfiles = glob.glob(self.plotspath+"*")
		for f in imgfiles:
			os.remove(f)	# remove temp jpg files from OutputFiles dir
		#events={"min_magnitude": 6.5}	
	
		# Initialize multiprocessing pools for plotting
		cpu_count = multiprocessing.cpu_count()
		PROCESSES = cpu_count
		pool = multiprocessing.Pool(PROCESSES)
		try:
			print "Starting Pool map plotVelocity()"	
			pool.map(unwrap_self_plotVelocity, zip([self]*streamlen, streams, self.stationName))	# thread plots
			
			pool.close()
			pool.join()
			pool.terminate()
			pool.join()
		except KeyboardInterrupt:
			print "Caught KeyboardInterrupt: terminating plotVelocity() workers"
			pool.terminate()
			pool.join()
			sys.exit(0)
			print "Pool plotVelocity() is terminated"
		except Exception, e:
			print "Get exception: %r, terminating the Pool" % (e,)
			pool.terminate()
			pool.join()
			sys.exit(0)
			print "Pool plotVelocity() is terminated"

	def __init__(self, **kwargs):
		# -----------------------------------------
		# Open cwb config file and read in lines
		# 1) Station info
		# 2) Date/time info for station
		# 3) Duration of signal
		# -----------------------------------------
		fin = open('station.cfg', 'r')
		data = {}	# dict of cwb config data
		data['station'] = []	# list for multiple stations
		STFLAG = False	
		for line in fin:
			if line[0] == '#':
				if line != '\n':
					newline = re.split('#', line)
					if "Station Data" in newline[1]:
						STFLAG = True
			elif line[0] != '#':
				if line != '\n':
					newline = re.split('#', line)	
					if STFLAG:
						data['station'].append(line.strip())
					elif "duration" in newline[1]:
						self.duration = float(newline[0].strip())
					elif "ipaddress" in newline[1]:
						self.ipaddress = str(newline[0].strip())
					elif "httpport" in newline[1]:
						self.httpport = int(newline[0].strip())
					elif "magnification default" in newline[1]:
						self.magnification_default = float(newline[0].strip())
					elif "xres" in newline[1]:
						self.resx = int(newline[0].strip())
					elif "yres" in newline[1]:
						self.resy = int(newline[0].strip())
					elif "pixels" in newline[1]:
						self.pix = int(newline[0].strip())
					elif "image format" in newline[1]:
						self.imgformat = str(newline[0].strip())
					elif "vertical" in newline[1]:
						self.vertrange = float(newline[0].strip())
					elif "seed" in newline[1]:
						self.seedpath = str(newline[0].strip())
					elif "plots" in newline[1]:
						self.plotspath = str(newline[0].strip())
					elif "cwbquery" in newline[1]:
						self.cwbquery = str(newline[0].strip())
					elif "responses" in newline[1]:
						self.resppath = str(newline[0].strip())
					elif "EHZ filter" in newline[1]:
						self.EHZfiltertype = str(newline[0].strip())
					elif "EHZ prefilt f1" in newline[1]:
						self.EHZprefiltf1 = float(newline[0].strip())
					elif "EHZ prefilt f2" in newline[1]:
						self.EHZprefiltf2 = float(newline[0].strip())
					elif "EHZ prefilt f3" in newline[1]:
						self.EHZprefiltf3 = float(newline[0].strip())
					elif "EHZ prefilt f4" in newline[1]:
						self.EHZprefiltf4 = float(newline[0].strip())
					elif "EHZ highpass" in newline[1]:
						self.EHZhpfreq = float(newline[0].strip())
					elif "EHZ notch" in newline[1]:
						self.EHZnotchfreq = float(newline[0].strip())
					elif "BHZ filter" in newline[1]:
						self.BHZfiltertype = str(newline[0].strip())
					elif "BHZ prefilt f1" in newline[1]:
						self.BHZprefiltf1 = float(newline[0].strip())
					elif "BHZ prefilt f2" in newline[1]:
						self.BHZprefiltf2 = float(newline[0].strip())
					elif "BHZ prefilt f3" in newline[1]:
						self.BHZprefiltf3 = float(newline[0].strip())
					elif "BHZ prefilt f4" in newline[1]:
						self.BHZprefiltf4 = float(newline[0].strip())
					elif "BHZ bplower" in newline[1]:
						self.BHZbplowerfreq = float(newline[0].strip())
					elif "BHZ bpupper" in newline[1]:
						self.BHZbpupperfreq = float(newline[0].strip())
					elif "LHZ filter" in newline[1]:
						self.LHZfiltertype = str(newline[0].strip())
					elif "LHZ prefilt f1" in newline[1]:
						self.LHZprefiltf1 = float(newline[0].strip())
					elif "LHZ prefilt f2" in newline[1]:
						self.LHZprefiltf2 = float(newline[0].strip())
					elif "LHZ prefilt f3" in newline[1]:
						self.LHZprefiltf3 = float(newline[0].strip())
					elif "LHZ prefilt f4" in newline[1]:
						self.LHZprefiltf4 = float(newline[0].strip())
					elif "LHZ bplower" in newline[1]:
						self.LHZbplowerfreq = float(newline[0].strip())
					elif "LHZ bpupper" in newline[1]:
						self.LHZbpupperfreq = float(newline[0].strip())
					elif "VHZ filter" in newline[1]:
						self.VHZfiltertype = str(newline[0].strip())
					elif "VHZ prefilt f1" in newline[1]:
						self.VHZprefiltf1 = float(newline[0].strip())
					elif "VHZ prefilt f2" in newline[1]:
						self.VHZprefiltf2 = float(newline[0].strip())
					elif "VHZ prefilt f3" in newline[1]:
						self.VHZprefiltf3 = float(newline[0].strip())
					elif "VHZ prefilt f4" in newline[1]:
						self.VHZprefiltf4 = float(newline[0].strip())
					elif "VHZ lowpass" in newline[1]:
						self.VHZlpfreq = float(newline[0].strip())	
					elif "magnification exceptions" in newline[1]:
						self.magnificationexc = newline[0].strip()

		# Store station info/locations in variables
		self.stationdata = data['station']
		self.stationinfo = []
		self.stationlocation = []
		for s in self.stationdata:	
			tmpstation = re.split('\t', s)
			self.stationinfo.append(tmpstation[0].strip())
			self.stationlocation.append(tmpstation[1].strip())
	
		# Split/store magnification exception list
		tmpmag = re.split(',', self.magnificationexc)
		self.magnificationexc = {}
		for i in range(len(tmpmag)):
			tmpexc = re.split(':', tmpmag[i])
			self.magnificationexc[tmpexc[0].strip()] = float(tmpexc[1].strip())

		# Get current date/time and subtract a day
		# this will always pull the current time on the system
		time = datetime.utcnow() - timedelta(days=1)
		timestring = str(time)
		timestring = re.split("\\.", timestring)
		tmp = timestring[0]
		timedate = tmp.replace("-", "/")
		datetimeQuery = timedate.strip()
		#datetimeQuery = "2013/08/17 00:00:00"
		self.datetimeQuery = datetimeQuery
		tmpquery = re.split(' ', self.datetimeQuery)
		tmpdate = tmp[0].strip()
		tmptime = tmp[1].strip()
		print "\ndatetimeQuery = " + str(self.datetimeQuery) 
		tmpUTC = datetimeQuery
		tmpUTC = tmpUTC.replace("/", "")
		tmpUTC = tmpUTC.replace(" ", "_")
		self.datetimeUTC = UTCDateTime(str(tmpUTC))
		print "datetimeUTC = " + str(self.datetimeUTC) + "\n"

# -----------------------------
# Main program (can be removed)
# -----------------------------
if __name__ == '__main__':
	heli = HeliPlot()
	heli.parallelcwbQuery()			# query stations
	heli.pullTraces()			# analyze trace data and remove empty traces	
	heli.freqResponse()			# calculate frequency response of signal	
	heli.parallelfreqDeconvFilter()		# deconvolve/filter trace data	
	magnified_streams = heli.magnifyData()	# magnify trace data 
	heli.parallelPlotVelocity(magnified_streams)			# plot filtered/magnified data	
