#/usr/bin/python
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.stream import read
from obspy.signal.invsim import evalresp
import warnings, glob, re, os, sys, string, subprocess
from datetime import datetime, timedelta

# ---------------------------------------------------------
# HeliPlot() uses CWBQuery to query station streams,
# streams are then filtered and plotted using ObsPy
# ---------------------------------------------------------
class HeliPlot(object):
	def cwbQuery(self):
		# ------------------------------------------------
		# Pull specific station seed file using CWBQuery
		# ------------------------------------------------
		files = glob.glob(self.seedpath+"*")
		for f in files:
			os.remove(f)	# remove temp seed files from SeedFiles dir
		stationlen = len(self.stationinfo)
	
		# Get current date/time and subtract a day
		# this will always pull the current time on the system
		time = datetime.now() - timedelta(days=1)
		timestring = str(time)
		timestring = re.split("\\.", timestring)
		tmp = timestring[0]
		timedate = tmp.replace("-", "/")
		#datetimeQuery = timedate.strip()
		datetimeQuery = "2013/08/17 00:00:00"
		print "\ndatetimeQuery = " + str(datetimeQuery) + "\n"
		tmpUTC = datetimeQuery
		tmpUTC = tmpUTC.replace("/", "")
		tmpUTC = tmpUTC.replace(" ", "_")
		datetimeUTC = UTCDateTime(str(tmpUTC))

		for i in range(stationlen):	# cwbquery on each operable station
			try:
				proc = subprocess.Popen(["java -jar  " + self.cwbquery + " -s " + '"'+self.stationinfo[i]+'"' + " -b " + '"'+datetimeQuery+'"' + " -d " + '"'+str(self.duration)+'"' + " -t ms -o " + self.seedpath+"%N_%y_%j -h " + '"'+self.ipaddress+'"'], stdout=subprocess.PIPE, shell=True)
				(out, err) = proc.communicate()
				print out
			except Exception as e:
				print "*****Exception found = " + str(e)

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
			print "number of traces = " + str(tracelen)
			print "len(trace[i]) = " + str(len(trace[index]))
			print strsel
			if tracelen == 1:
				if trace[index].stats['sampling_rate'] == 0.0:
					stream[i].remove(trace[index])
			elif tracelen > 1:
				for j in range(tracelen):
					if trace[index][j].stats['sampling_rate'] == 0.0:
						stream[i].remove(trace[index][j])

	def freqDeconvFilter(self):
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

		# -------------------------------------------------------------------
		# Loop through stations and get frequency responses for each stream
		# -------------------------------------------------------------------
		# Pre-filter bandpass corner frequencies eliminate end frequency
		# spikes (i.e. H(t) = F(t)/G(t), G(t) != 0)
		# -------------------------------------------------------------------
		stationName = []	# station names for output plots
		for i in range(self.streamlen):
			# NOTE: For aslres01 frequency responses are 
			# contained in /APPS/metadata/RESPS/
			resfilename = "RESP."+networkID[i]+"."+stationID[i]+"."+locationID[i]

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
		for line in fin:
			if (line[0] != '#'):
				if line != '\n':
					newline = re.split('#', line)
					if "station" in newline[1]:
						data['station'].append(newline[0].strip())
					elif "duration" in newline[1]:
						data['duration'] = newline[0].strip()
					elif "ipaddress" in newline[1]:
						data['ipaddress'] = newline[0].strip()
					elif "httpport" in newline[1]:
						data['httpport'] = newline[0].strip()
					elif "filter" in newline[1]:
						data['filtertype'] = newline[0].strip()
					elif "bplower" in newline[1]:
						data['bplowerfreq'] = newline[0].strip()
					elif "bpupper" in newline[1]:
						data['bpupperfreq'] = newline[0].strip()
					elif "lp" in newline[1]:
						data['lpfreq'] = newline[0].strip()
					elif "hp" in newline[1]:
						data['hpfreq'] = newline[0].strip()
					elif "notch" in newline[1]:
						data['notch'] = newline[0].strip()
					elif "magnification" in newline[1]:
						data['magnification'] = newline[0].strip()
					elif "xres" in newline[1]:
						data['resx'] = newline[0].strip()
					elif "yres" in newline[1]:
						data['resy'] = newline[0].strip()
					elif "pixels" in newline[1]:
						data['pix'] = newline[0].strip()
					elif "vertical" in newline[1]:
						data['vertrange'] = newline[0].strip()
					elif "c1" in newline[1]:
						data['c1'] = newline[0].strip()
					elif "c2" in newline[1]:
						data['c2'] = newline[0].strip()
					elif "c3" in newline[1]:
						data['c3'] = newline[0].strip()
					elif "c4" in newline[1]:
						data['c4'] = newline[0].strip()
					elif "seed" in newline[1]:
						data['seedpath'] = newline[0].strip()
					elif "plots" in newline[1]:
						data['plotspath'] = newline[0].strip()
					elif "cwbquery" in newline[1]:
						data['cwbquery'] = newline[0].strip()
					elif "responses" in newline[1]:
						data['resppath'] = newline[0].strip()
	
		# Store data in variables
		self.stationinfo = data['station']
		self.duration = float(data['duration'])
		self.ipaddress = str(data['ipaddress'])
		self.httpport = int(data['httpport'])
		self.filtertype = str(data['filtertype'])
		self.magnification = float(data['magnification'])
		self.resx = int(data['resx'])
		self.resy = int(data['resy'])
		self.pix = int(data['pix'])
		self.vertrange = float(data['vertrange'])
		self.c1 = float(data['c1'])
		self.c2 = float(data['c2'])
		self.c3 = float(data['c3'])
		self.c4 = float(data['c4'])
		self.seedpath = str(data['seedpath'])
		self.plotspath = str(data['plotspath'])
		self.cwbquery = str(data['cwbquery'])
		self.resppath = str(data['resppath'])
		if self.filtertype == "bandpass":
			self.bplowerfreq = float(data['bplowerfreq'])
			self.bpupperfreq = float(data['bpupperfreq'])
		elif self.filtertype == "lowpass":
			self.lpfreq = float(data['lpfreq'])
		elif filtertype == "highpass":
			self.hpfreq = float(data['hpfreq'])
		elif filtertype == "notch":
			self.notch = float(data['notch'])

# -----------------------------
# Main program (can be removed)
# -----------------------------
if __name__ == '__main__':
	heli = HeliPlot()
	heli.cwbQuery()
	heli.pullTraces()	
