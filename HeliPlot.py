#!/usr/bin/env python

# -----------------------------------------------------------------
# Author: Alejandro Gonzales
# Filename: HeliPlot.py
# -----------------------------------------------------------------
# Purpose: Script reads in configurations from station.cfg and 
# queries stations, station data is then deconvolved, filtered, 
# magnified and plotted. Outputs will be station data images in
# a jpg format. When script is finished processing, run
# run_heli_24hr.py to generate HTML files for each station
# -----------------------------------------------------------------
# Methods (keyword search):
#	* parallelcwbQuery()
#	* cwbQuery()
#	* pullTraces()
#	* freqResponse()
#	* parallelfreqDeconvFilter()
#	* freqDeconvFilter()
#	* magnifyData()
#	* parallelPlotVelocity()
#	* plotVelocity()
#	* createThumbnails()
# -----------------------------------------------------------------
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt	# will use title, figure, savefig methods
import matplotlib.image as img

from obspy.core.utcdatetime import UTCDateTime
from obspy.core.stream import read
from obspy.signal.invsim import evalresp
from multiprocessing import Manager, Value
import numpy as np
import functools
import multiprocessing
import warnings, glob, re, os, sys, string, subprocess
from datetime import datetime, timedelta
import signal, logging, psutil, time
#from matplotlib.pyplot import title, figure, savefig


class KeyboardInterruptError(Exception): pass	# raises KeyboardInterrupts for multiprocessing methods

class TimeoutExpiredError(Exception): pass	# raises TimeoutExpired errors for multiprocessing subprocess methods

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
	def killSubprocess(self, proc, signum):
		# -----------------------------
		# Kills pool subprocess child
		# proc.kill()
		# os.kill(proc.pid, signum)
		# kill = os.killpg(proc.pid, signum)
		# -----------------------------
		print "Killing child %6s" % proc.pid	
		time.sleep(1)	
		# Add conditional statement deciphering
		# timeout errors from keyboard interrupts
		(out, err) = proc.communicate()
		print out
		print err
		sys.stdout.flush()
		sys.stderr.flush()

	def killPool(self, pool, pid, name):
		# ------------------------------
		# Kills pool including children	
		# sys.exit(0)
		# os.wait()	# wait for all threads to terminate
		# ------------------------------	
		# find/kill all child processes (mpEvent/poolClose)
		pool.terminate()
		pool.join()
		time.sleep(1)
		print "Pool %s is terminated" % name
		parent = psutil.Process(pid)
		# set recursive=True to kill grandchildren	
		print "Killing children of pool %6s..." % pid	
		time.sleep(1)	
		for child in parent.get_children(recursive=True):
			child.kill()	# kill children of pool 
		print "Killing pool %6s..." % pid
		time.sleep(1)	
		parent.kill()	# kill pool (parent)

	def cwbQuery(self, station): 
		# ------------------------------------------------
		# Pull specific station seed file using CWBQuery
		# ------------------------------------------------
		for attempt in range(self.cwbattempts):
			try:
				# -----------------------------------------------------------	
				# Print CWBQuery() contents	
				#print "java -jar " + self.cwbquery +\
				#	" -s " + '"'+station+'"' + " -b " + '"'+self.datetimeQuery+'"' +\
				#	" -d " + '"'+str(self.duration)+'"' + " -t dcc512 -o " +\
				#	self.seedpath+"%N_%y_%j -h " + '"'+self.ipaddress+'"'	
				# -----------------------------------------------------------	
			
				# subprocess.Popen() needs to have a logger to track
				# child process hangs (zombies). Also need to introduce
				# a block that will kill all child processes if there
				# is an error exception. All errors/warnings/info should
				# be logged
				proc = subprocess.Popen(["java -jar " + self.cwbquery +\
					" -s " + '"'+station+'"' + " -b " + '"'+self.datetimeQuery+'"' +\
					" -d " + '"'+str(self.duration)+'"' + " -t dcc512 -o " +\
					self.seedpath+"%N_%y_%j -h " + '"'+self.ipaddress+'"'],\
					stdout=subprocess.PIPE, stderr=subprocess.PIPE,\
					preexec_fn=os.setsid, shell=True)
				(out, err) = proc.communicate(timeout=self.cwbtimeout)	# waits for child proc 
				print proc.pid	
				print out 
				print err 	
				sys.stdout.flush()
				sys.stderr.flush()
			except subprocess.TimeoutExpired:
				print "TimeoutExpired Warning (cwbQuery() subprocess): retrying (attempt %d)..." % attempt
				time.sleep(self.cwbsleep)

				if attempt == (self.cwbattempts-1):
					print "TimeoutExpired (cwbQuery() subprocess): terminate cwbQuery() workers"	
					self.killSubprocess(proc, signal.SIGKILL)	
					raise TimeoutExpiredError()
					return	# returns to cwbQuery pool	
			except KeyboardInterrupt:
				print "KeyboardInterrupt (cwbQuery() subprocess): terminate cwbQuery() workers"	
				self.killSubprocess(proc, signal.SIGKILL)	
				raise KeyboardInterruptError()	
				return	
			except Exception as e:
				print "*****Exception (cwbQuery() subprocess): " + str(e)
				self.killSubprocess(proc, signal.SIGKILL)	
				return	
			else:
				break
	
	def parallelcwbQuery(self):
		# --------------------------------------------------
		# Initialize all variables needed to run cwbQuery()
		# --------------------------------------------------
		print "--------cwbQuery() Pool-------\n"	
		self.home = os.getcwd()
		files = glob.glob(self.seedpath+"*")
		for f in files:
			os.remove(f)	# remove tmp seed files from SeedFiles dir
		stationlen = len(self.stationinfo)

		# -----------------------------------------------
		# Create multiprocessing pools to run multiple 
		# instances of cwbQuery()
		# -----------------------------------------------
		PROCESSES = multiprocessing.cpu_count()
		print "PROCESSES = " + str(PROCESSES)
		print "cwbtimeout = " + str(self.cwbtimeout)
		print "cwbattempts = " + str(self.cwbattempts)
		print "cwbsleep = " + str(self.cwbsleep)	
		pool = multiprocessing.Pool(PROCESSES)
		try:
			poolpid = os.getpid()	
			poolname = "cwbQuery()"	
			print "pool PID = " + str(poolpid) + "\n"	
			pool.map(unwrap_self_cwbQuery, zip([self]*stationlen, self.stationinfo))
		
			# pool.close()/pool.terminate() must be called before pool.join() 
			# pool.close(): prevents more tasks from being submitted to pool, 
			# once tasks have been completed the worker processes will exit
			# pool.terminate(): stops worker processes immediately without completing
			# outstanding work, when the pool object is garbage collected terminate() 
			# will be called immediately
			# pool.join(): wait for worker processes to exit 
			pool.close()	
			pool.join()	
			print "-------cwbQuery() Pool Complete------\n\n"
		except TimeoutExpiredError:
			print "TimeoutExpiredError (parallelcwbQuery() pool): terminating cwbQuery() workers"
			# find/kill all child processes 
			self.killPool(pool, poolpid, poolname)	
		except KeyboardInterrupt:
			print "KeyboardInterruptError (parallelcwbQuery() pool): terminating cwbQuery() workers"
			self.killPool(pool, poolpid, poolname)	
		except Exception, e:
			print "Exception (parallelcwbQuery() pool): %r, terminating the Pool" % (e,)
			self.killPool(pool, poolpid, poolname)

	def pullTraces(self):
		# ------------------------------------------------
		# Open seed files from cwbQuery and pull trace
		# stats from the data stream
		# ------------------------------------------------
		print "------pullTraces() Start-------\n" 
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
				print "*****Exception (pullTraces(), read(MSEED)): " + str(e)
				sys.exit(0)
				print "Method pullTraces() is terminated!"
			i = i - 1
		
		try:
			streamlen = len(stream)	# number of streams (i.e. stream files)
			self.streamlen = streamlen	
			print "streamlen = " + str(self.streamlen) 
			trace = {}	# dict of traces for each stream
			print "Creating trace dictionary based on stream indexing..."
			print "multiple traces constitute embedded lists within dict."
			for i in range(streamlen):
				strsel = stream[i]	# selected stream
				#tracelen = len(strsel)	# number of traces in stream
				tracelen = strsel.count()	
				tmp_trace_id = strsel[0].getId()	
				index = str(i)
				if tracelen == 1:	# single trace stream
					trace[index] = strsel[0]	# trace 0 in stream[i]
				elif tracelen > 1:	# multiple trace stream
					trace[index] = []	# list in dict
					for j in range(tracelen):
						trace[index].append(strsel[j])

			# Loop through stream traces, if trace has sample rate = 0.0Hz
			# => NFFT = 0, then this trace will be removed
			print "Removing traces with 0.0Hz sampling rate from stream[][] list...\n"
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
			print "--------pullTraces() Complete------\n\n"
		except KeyboardInterrupt:
			print "KeyboardInterrupt (pullTraces() main()): terminating pullTraces() method"
			sys.exit(0)
			print "Method pullTraces() is terminated!"
		except Exception as e:
			print "*****Exception (pullTraces() main()): " + str(e)
			sys.exit(0)
			print "Method pullTraces() is terminated!"

	def freqResponse(self):
		# -----------------------------------------------------------
		# Pull frequency response for station and run a simulation
		# to deconvolve signal, after deconvolution filter signal
		# -----------------------------------------------------------
		print "--------freqResponse() Start--------\n"	
		os.chdir(self.resppath)	# cd into response directory
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

		try:
			# -------------------------------------------------------------------
			# Loop through stations and get frequency responses for each stream
			# -------------------------------------------------------------------
			stationName = []	# station names for output plots
			self.resp = []		# station frequency responses for deconvolution	
			for i in range(self.streamlen):
				# NOTE: For aslres01 frequency responses are 
				# contained in /APPS/metadata/RESPS/
				# Check for empty location codes, replace "__" with ""	
				if locationID[i] == "__":
					locationID[i] = ""
				resfilename = "RESP."+networkID[i]+"."+stationID[i]+"."+locationID[i]+"."+channelID[i]	# response filename
				print "resfilename = " + str(resfilename)
				tmpname = re.split('RESP.', resfilename) 	
				stationName.append(tmpname[1].strip())	
				self.stationName = stationName	# store station names	
			
				resp = {'filename': resfilename, 'date': self.datetimeUTC, 'units': 'VEL'}	# frequency response of data stream in terms of velocity
				self.resp.append(resp)	
				print "stream[%d]" % i
				print "number of traces = " + str(len(self.stream[i]))
				print "datetimeUTC = " + str(self.datetimeUTC)
				print "\n"
			print "-------freqResponse() Complete------\n\n"
		except KeyboardInterrupt:
			print "KeyboardInterrupt (freqResponse()): terminating freqResponse() method" 
			sys.exit(0)
			print "Method freqResponse() is terminated!"
		except Exception as e:
			print "*****Exception (freqResponse()): " + str(e)
			sys.exit(0)
			print "Method freqResponse() is terminated!"

	def freqDeconvFilter(self, stream, response):
		# ----------------------------------------	
		# Filters are designed according to 
		# channel IDs. Each channel will present
		# a different sampling rate and thus 
		# a different filter.	
		# ----------------------------------------	
		# Make sure stream and response names match	
		tmpstr = re.split("\\.", stream[0].getId())
		namestr = tmpstr[1].strip()
		nameloc = tmpstr[2].strip()	
		namechan = tmpstr[3].strip()	
		nameres = response['filename'].strip() 
		if namechan == "EHZ":
			filtertype = self.EHZfiltertype
			hpfreq = self.EHZhpfreq
			notchfreq = self.EHZnotchfreq	# notch filter will be implemented later
		elif namechan == "BHZ":
			filtertype = self.BHZfiltertype
			bplowerfreq = self.BHZbplowerfreq	
			bpupperfreq = self.BHZbpupperfreq	
		elif namechan == "LHZ":
			filtertype = self.LHZfiltertype
			bplowerfreq = self.LHZbplowerfreq
			bpupperfreq = self.LHZbpupperfreq	
		elif namechan == "VHZ":
			filtertype = self.VHZfiltertype
			lpfreq = self.VHZlpfreq
			
		# Try/Catch block for Sensitivity Subprocess	
		# exceptions will be included for filters	
		try:	
			print "Filter stream " + namestr + " and response " + nameres 
			print namechan + " filtertype = " + str(filtertype) 
			
			# Deconvolution (remove sensitivity)
			sensitivity = "Sensitivity:"	# pull sensitivity from RESP file
			grepSensitivity = "grep " + '"' + sensitivity + '"' + " " + nameres + " | tail -1"
			self.subprocess = True	# flag for exceptions (if !subprocess return)	
			proc = subprocess.Popen([grepSensitivity], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			(out, err) = proc.communicate(timeout=10)	# waits for child proc
			tmps = out.strip()
			tmps = re.split(':', tmps)
			s = float(tmps[1].strip())
			print "sensitivity = " + str(s) 
			sys.stdout.flush()
			sys.stderr.flush()
			self.subprocess = False	# subprocess finished

			# divide data by sensitivity	
			#stream.simulate(paz_remove=None, pre_filt=(c1, c2, c3, c4), seedresp=response, taper='True')	# deconvolution (this will be a flag for the user)
			
			stream[0].data = stream[0].data / s	# remove sensitivity gain from stream data
			# remove DC offset (transient resp) 
			stream.detrend('demean')	# removes mean in data set	
			stream.taper(p=0.01)	# tapers beginning/end to remove transient resp
			
			if filtertype == "bandpass":
				print "Filtering stream (bandpass)"
				print "bp lower freq = " + str(bplowerfreq) 
				print "bp upper freq = " + str(bpupperfreq) 
				stream.filter(filtertype, freqmin=bplowerfreq, freqmax=bpupperfreq, corners=4)	# bandpass filter design
			elif filtertype == "lowpass":
				print "Filtering stream (lowpass)"
				print "lp freq = " + str(lpfreq) 
				stream.filter(filtertype, freq=lpfreq, corners=4)	# lowpass filter design
			elif filtertype == "highpass":
				print "Filtering stream (highpass)"
				print "hpfreq = " + str(hpfreq) 
				stream.filter(filtertype, freq=hpfreq, corners=4)	# highpass filter design	

			print "Filtered stream = " + str(stream) + "\n"	
			return stream 
		except subprocess.TimeoutExpired:
			print "TimeoutExpired (freqDeconvFilter() subprocess): terminate freqDeconvFilter() workers"	
			if self.subprocess:		
				self.killSubprocess(proc, signal.SIGKILL)
			raise TimeoutExpiredError()
			return	# return to freqDeconvFilter pool
		except KeyboardInterrupt:
			print "KeyboardInterrupt (freqDeconvFilter() subprocess): terminate freqDeconvFilter() workers"
			# if interrupt during subprocess kill child else return	
			if self.subprocess:	
				self.killSubprocess(proc, signal.SIGKILL)
			raise KeyboardInterruptError()
			return
		except Exception as e:
			print "*****Exception (freqDeconvFilter() subprocess): " + str(e)
			# if exception during subprocess kill child else return	
			if self.subprocess:	
				self.killSubprocess(proc, signal.SIGKILL)
			return
	
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
		print "------freqDeconvFilter() Pool------\n"	
		for i in range(self.streamlen):	
			self.stream[i].merge(method=1, fill_value='interpolate', interpolation_samples=100)	# merge traces to eliminate small data lengths, method 0 => no overlap of traces (i.e. overwriting of previous trace data)

		# Deconvolution/Prefilter	
		# Initialize multiprocessing pools
		PROCESSES = multiprocessing.cpu_count()
		print "PROCESSES = " + str(PROCESSES) 	
		pool = multiprocessing.Pool(PROCESSES)
		try:
			poolpid = os.getpid()	
			poolname = "freqDeconvFilter()"
			print "pool PID = " + str(poolpid) + "\n"
			flt_streams = pool.map(unwrap_self_freqDeconvFilter, zip([self]*self.streamlen, self.stream, self.resp))	
			
			pool.close()
			pool.join()	
			
			self.flt_streams = flt_streams
			print "-------freqDeconvFilter() Pool Complete------\n\n"
		except TimeoutExpiredError:
			print "TimeoutExpiredError (parallelfreqDeconvFilter() pool): terminating freqDeconvFilter() workers"
			# find/kill all child processes
			self.killPool(pool, poolpid, poolname)
		except KeyboardInterrupt:
			print "KeyboardInterruptError (parallelfreqDeconvFilter() pool): terminating freqDeconvFilter() workers"
			self.killPool(pool, poolpid, poolname)
		except Exception, e:
			print "Exception (parallelfreqDeconvFilter() pool): %r, terminating the Pool" % (e,)
			self.killPool(pool, poolpid, poolname)

	def magnifyData(self):
		# ----------------------------------------
		# Magnify streams by specified 
		# magnification factor 
		# ----------------------------------------
		print "-----magnifyData() Start------\n"	
		streams = self.flt_streams	
		streamlen = len(streams)
		print "Num filtered streams = " + str(streamlen)	
		self.magnification = {}	# dict containing magnifications for each station	
		try:	
			for i in range(streamlen):
				tracelen = streams[i].count()	
				if tracelen == 1:
					tr = streams[i][0]	# single trace within stream
					data = tr.data		# data samples from single trace
					datalen = len(data)	# number of data points within single trace
					tmpId = re.split("\\.", tr.getId())	# stream ID
					networkId = tmpId[0].strip()		# network ID	
					stationId = tmpId[1].strip()		# station ID
					netstationId = networkId + stationId	# network/station

					print "Magnifying stream " + str(tr.getId()) 
					if netstationId in self.magnificationexc:	
						magnification = self.magnificationexc[netstationId]
					else:
						magnification = self.magnification_default
					print "magnification = " + str(magnification) + "\n"
					self.magnification[streams[i][0].getId()] = magnification
					streams[i][0].data = streams[i][0].data * magnification 
		
			print "------magnifyData() Complete------\n\n"	
			return streams	
		except KeyboardInterrupt:
			print "KeyboardInterrupt (magnifyData()): terminating magnifyData() method"
			sys.exit(0)
			print "Method magnifyData() is terminated!"
		except Exception as e:
			print "*****Exception (magnifyData()): " + str(e)
			sys.exit(0)
			print "Method magnifyData() is terminated!"

	def plotVelocity(self, stream, stationName):
		# --------------------------------------------------------
		# Plot velocity data	
		# --------------------------------------------------------
		#stream.merge(method=1, fill_value='interpolate', interpolation_samples=100)	# for gapped/overlapped data run a linear interpolation with 100 samples
		try:
			print "Plotting velocity data for station " + str(stationName) 
			magnification = self.magnification[stream[0].getId()]	# magnification for station[i]
			trspacing = self.vertrange/magnification * 1000.0	# trace spacing	
			tmpstr = re.split("\\.", stream[0].getId())
			namechan = tmpstr[3].strip()
			if namechan == "EHZ":
				filtertype = self.EHZfiltertype	
				hpfreq = self.EHZhpfreq
				notchfreq = self.EHZnotchfreq	
				bounds = str(hpfreq)	
			elif namechan == "BHZ":
				filtertype = self.BHZfiltertype
				bplowerfreq = self.BHZbplowerfreq	
				bpupperfreq = self.BHZbpupperfreq	
				bounds = str(bplowerfreq) + "-" + str(bpupperfreq)	
			elif namechan == "LHZ":
				filtertype = self.LHZfiltertype
				bplowerfreq = self.LHZbplowerfreq
				bpupperfreq = self.LHZbpupperfreq	
				bounds = str(bplowerfreq) + "-" + str(bpupperfreq)	
			elif namechan == "VHZ":
				filtertype = self.VHZfiltertype
				lpfreq = self.VHZlpfreq
				bounds = str(lpfreq)

			# pass explicit figure instance to set correct title and attributes	
			dpl = plt.figure()	
			titlestartTime = self.datetimePlotstart.strftime("%Y/%m/%d %H:%M")	
			titlestartTime = titlestartTime + " UTC"	
			stream.plot(starttime=self.datetimePlotstart, endtime=self.datetimePlotend,\
				type='dayplot', interval=60,\
				vertical_scaling_range=self.vertrange,\
				right_vertical_labels=False, number_of_ticks=7,\
				one_tick_per_line=True, color=['k'], fig=dpl,\
				show_y_UTC_label=False, size=(self.resx,self.resy),\
				dpi=self.pix, title_size=-1)
		
			
			# Set title, x/y labels and tick marks	
			plt.title(stream[0].getId() + "  " + "Start: " +\
				str(titlestartTime), fontsize=12) 
			plt.xlabel('Time [m]\n(%s: %sHz  Trace Spacing: %.2e mm/s)' %\
			(str(filtertype), str(bounds), trspacing), fontsize=10)	
			plt.ylabel('Time [h]', fontsize=10)	
			locs, labels = plt.yticks()	# pull current locs/labels	
			hours = [0 for i in range(len(labels))]		
			for i in range(len(labels)):	# extract hours from labels
				tmptime = re.split(':', labels[i].get_text())	
			 	hours[i] = int(tmptime[0]) 
			posilist = [i+0.5 for i in range(24)]	# create tick position list
			posilist = posilist[::-1]	# reverse list	
			timelist = [0 for i in range(24)]	# timelist for tick hours
			timelen = len(timelist)	
			starthr = hours[0]	# start hour 	
			if starthr < 23:
				startlen = 23 - starthr + 1	# hours are from 0-23
			else:
				startlen = 0
			startlist = range(starthr, starthr+startlen)	# start of list 0-23 
			startlen = len(startlist)	
			timelist[0:startlen] = startlist	# end of start should be 23	
			timelist[startlen:timelen] = range(0, timelen-startlen) 
			for i in range(len(timelist)):
				timelist[i] = str(timelist[i]) + ":00"
			plt.yticks(posilist, timelist, fontsize=9)	
			print "\n"	
			#dpi=self.pix, size=(self.resx,self.resy))
			plt.savefig(stationName+"."+self.imgformat) 

		except KeyboardInterrupt:
			print "KeyboardInterrupt (plotVelocity()): terminate plotVelocity() workers"
			raise KeyboardInterruptError()
			return	# returns to plotVelocity() pool	
		except Exception as e:
			print "*****Exception (plotVelocity()): " + str(e)
			return	# returns to plotVelocity() pool	

	def parallelPlotVelocity(self, streams):	
		# --------------------------------------------------------
		# Plot velocity data	
		# events={"min_magnitude": 6.5} 	
		# --------------------------------------------------------
		print "------plotVelocity() Pool------\n"	
		streamlen = len(streams)	
		# clear outputplots directory	
		os.chdir(self.plotspath)	
		imgfiles = glob.glob(self.plotspath+"*")
		for f in imgfiles:
			os.remove(f)	# remove temp png files from OutputPlots dir
	
		# Initialize multiprocessing pools for plotting
		PROCESSES = multiprocessing.cpu_count()
		print "PROCESSES = " + str(PROCESSES)	
		pool = multiprocessing.Pool(PROCESSES)
		try:
			poolpid = os.getpid()
			poolname = "plotVelocity()"
			print "pool PID = " + str(poolpid) + "\n"
			pool.map(unwrap_self_plotVelocity, zip([self]*streamlen, streams, self.stationName))	# thread plots
			
			pool.close()
			pool.join()
			print "------plotVelocity() Pool Complete------\n\n"
		except KeyboardInterrupt:
			print "KeyboardInterruptError (parallelplotVelocity() pool): terminating plotVelocity() workers"
			# find/kill all child processes 	
			self.killPool(pool, poolpid, poolname)
		except Exception, e:
			print "Exception (parallelplotVelocity() pool): %r, terminating the Pool" % (e,)
			self.killPool(pool, poolpid, poolname)

	def createThumbnails(self):
		# --------------------------------------------------------
		# Create thumbnails from heli output plots (350x262)	
		# --------------------------------------------------------
		print "Creating Thumbnails from OutputPlots...\n"	
		# clear thumbnails directory 
		os.chdir(self.thumbpath)	# cd into Thumbnails directory	
		'''
		thmfiles = glob.glob(self.thumbpath+"*")
		for f in thmfiles:
			os.remove(f)	# rm temp thumbnail files from Thumbnails dir
		'''
		
		# read from outputplots directory
		imgfiles = glob.glob(self.plotspath+"*")
		for f in imgfiles:
			tmp = re.split('/', f)
			tmplen = len(tmp)
			fname = tmp[tmplen-1].strip()	# pull image name	
			tmp = re.split('\.', fname)
			fout = tmp[1].strip()	# pull station name
			fout = fout + "_24hr.png"	# append png
			img.thumbnail(f, fout, scale=0.4375)	

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
					elif "cwbquery timeout" in newline[1]:
						self.cwbtimeout = int(newline[0].strip())
					elif "cwbquery attempts" in newline[1]:
						self.cwbattempts = int(newline[0].strip())
					elif "cwbquery sleep" in newline[1]:
						self.cwbsleep = int(newline[0].strip())
					elif "seed" in newline[1]:
						self.seedpath = str(newline[0].strip())
					elif "plots" in newline[1]:
						self.plotspath = str(newline[0].strip())
					elif "thumbnails" in newline[1]:
						self.thumbpath = str(newline[0].strip())
					elif "cwbquery" in newline[1]:
						self.cwbquery = str(newline[0].strip())
					elif "responses" in newline[1]:
						self.resppath = str(newline[0].strip())
					elif "EHZ filter" in newline[1]:
						self.EHZfiltertype = str(newline[0].strip())
					elif "EHZ highpass" in newline[1]:
						self.EHZhpfreq = float(newline[0].strip())
					elif "EHZ notch" in newline[1]:
						self.EHZnotchfreq = float(newline[0].strip())
					elif "BHZ filter" in newline[1]:
						self.BHZfiltertype = str(newline[0].strip())
					elif "BHZ bplower" in newline[1]:
						self.BHZbplowerfreq = float(newline[0].strip())
					elif "BHZ bpupper" in newline[1]:
						self.BHZbpupperfreq = float(newline[0].strip())
					elif "LHZ filter" in newline[1]:
						self.LHZfiltertype = str(newline[0].strip())
					elif "LHZ bplower" in newline[1]:
						self.LHZbplowerfreq = float(newline[0].strip())
					elif "LHZ bpupper" in newline[1]:
						self.LHZbpupperfreq = float(newline[0].strip())
					elif "VHZ filter" in newline[1]:
						self.VHZfiltertype = str(newline[0].strip())
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
		#time = datetime(2014, 1, 13, 12, 15, 0, 0) - timedelta(days=1)	# earthquake
		time2 = time + timedelta(hours=1)	
		time2str = time2.strftime("%Y%m%d_%H:00:00")
		time3 = time2 + timedelta(days=1)
		time3str = time3.strftime("%Y%m%d_%H:00:00")
		self.datetimePlotstart = UTCDateTime(time2str)
		self.datetimePlotend = UTCDateTime(time3str)
		print "datetimePlotstart = " + str(self.datetimePlotstart)
		print "datetimePlotend = " + str(self.datetimePlotend)
		timestring = str(time)
		timestring = re.split("\\.", timestring)
		tmp = timestring[0]
		timedate = tmp.replace("-", "/")
		datetimeQuery = timedate.strip()
		#datetimeQuery = "2013/09/12 13:30:00"
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
	heli.parallelPlotVelocity(magnified_streams)	# plot filtered/magnified data	
	heli.createThumbnails()			# create thumbnails from output plots 
