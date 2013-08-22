#/usr/bin/python
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.stream import read
from obspy.signal.invsim import evalresp
import warnings, glob, re, os, sys, string
import subprocess
from datetime import datetime, timedelta

# ----------------------------------------------
# Open cwb config file and read in lines
# 1) Station info
# 2) Date/time info for station
# 3) Duration of signal
# ----------------------------------------------
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

# ----------------------------------------------------------------
# Run cwb query to extract stream from server
# Jar file executable:
# java -jar CWBQuery.jar -s "IUANMO LHZ00" -b "2013/07/29 00:00:00" -d 3600 -t ms -o %N_%y_%j -hp
# java -jar CWBQuery.jar -s "IUANMO LHZ00" -b "2013/07/29 00:00:00" -d 3600 -t ms -o %N_%y_%j -h136.177.121.27
# ----------------------------------------------------------------

# --------- times will be computed here
# -----------------------------------
stationinfo = data['station']
duration = float(data['duration'])
ipaddress = str(data['ipaddress'])
httpport = int(data['httpport'])
filtertype = str(data['filtertype'])
magnification = float(data['magnification'])
c1 = float(data['c1'])
c2 = float(data['c2'])
c3 = float(data['c3'])
c4 = float(data['c4'])
seedpath = str(data['seedpath'])
plotspath = str(data['plotspath'])
cwbquery = str(data['cwbquery'])
resppath = str(data['resppath'])
if filtertype == "bandpass":
	bplowerfreq = float(data['bplowerfreq'])
	bpupperfreq = float(data['bpupperfreq'])
elif filtertype == "lowpass":
	lpfreq = float(data['lpfreq'])
elif filtertype == "highpass":
	hpfreq = float(data['hpfreq'])
elif filtertype == "notch":
	notch = float(data['notch'])

# ------------------------------------------------
# Pull specific station seed file using CWBQuery
# ------------------------------------------------
files = glob.glob(seedpath+"*")
for f in files:
	os.remove(f)	# remove temp seed files from SeedFiles dir
stationlen = len(stationinfo)

# Get current date/time and subtract a day
# This will always pull the current time on the system
time = datetime.now() - timedelta(days=1)
timestring = str(time)
timestring = re.split("\\.", timestring)
tmp = timestring[0]
timedate = tmp.replace("-", "/")
datetimeQuery = timedate.strip()
tmpUTC = datetimeQuery
tmpUTC = tmpUTC.replace("/", "")
tmpUTC = tmpUTC.replace(" ", "_")
datetimeUTC = UTCDateTime(str(tmpUTC))

for i in range(stationlen):	# cwbquery on each operable station
	try:	
		proc = subprocess.Popen(["java -jar " + cwbquery + " -s " + '"'+stationinfo[i]+'"' + " -b " + '"'+datetimeQuery+'"' + " -d " + '"'+str(duration)+'"' + " -t ms -o " + seedpath+"%N_%y_%j -h " + '"'+ipaddress+'"'], stdout=subprocess.PIPE, shell=True)
		(out, err) = proc.communicate()
		print out	
	except Exception as e:
		print "*****Exception found = " + str(e)

# --------------------------------------------------------
# Open seed files from cwbQuery.py 
# Pull trace stats from data stream
# --------------------------------------------------------
os.chdir(seedpath)
filelist = sorted(os.listdir(seedpath), key=os.path.getctime)
filelen = len(filelist)
stream = [0 for x in range(filelen)]	# multidim streams list, streams for each file contain multiple traces so streams = [][] where the second entry denotes the trace index 
i = filelen-1
while i >= 0: 
	try:	
		stream[i] = read(filelist[i])	# read MSEED files from query
	except Exception as e:
		print "******Exception found = " + str(e)	
	i = i - 1

streamlen = len(stream)	# number of streams (i.e. stream files) 
trace = {}	# dict of traces for each stream
nfft = 0	# number of fft points, necessary for some filtering
for i in range(streamlen):
	strsel = stream[i]	
	tracelen = len(strsel)	# number of traces in stream
	index = str(i)	
	if tracelen == 1:	# single trace stream
		trace[index] = strsel[0]	# trace 0 in stream i
		nfft = trace[index].count()	
	else:			# multiple trace stream
		trace[index] = []	# list in dict 
		nfft = 0
		for j in range(tracelen):	
			trace[index].append(strsel[j])
			tr = trace[index] 	
			nfft = nfft + tr[j].count() 

# Loop through stream traces, if trace has sample rate = 0.0Hz 
# => NFFT = 0 then this trace will be removed
for i in range(streamlen):
	strsel = stream[i]
	tracelen = len(strsel)
	index = str(i)
	if tracelen == 1:
		#print "Station = " + str(trace[index].stats['station'])	
		if trace[index].stats['sampling_rate'] == 0.0:
			#print "removed trace[%d]" % i 
			strsel.remove(trace[index])	
	else:
		#print "Station = " + str(trace[index][0].stats['station'])	
		for j in range(tracelen):	
			tr = trace[index]	
			if tr[j].stats['sampling_rate'] == 0.0:
				#print "removed trace[%d][%d]" % (i, j)	
				strsel.remove(tr[j])	

# ----------------------------------------------------------------
# Pull frequency response for station and run a simulation
# to deconvolve the signal
# ----------------------------------------------------------------
networkID = []
stationID = []
locationID = []
channelID = []
# Need stations listed in SeedFiles directory
for i in range(streamlen):
	tmpstation = filelist[i] 	
	stationindex = tmpstation.index('_')	
	networkID.append(str(tmpstation[0:2]))
	stationID.append(str(tmpstation[2:stationindex]))	
	locationindex = len(tmpstation)-11
	channelindex = len(tmpstation)-14
	locationID.append(str(tmpstation[locationindex:locationindex+2]))
	channelID.append(str(tmpstation[channelindex:channelindex+3]))

# ---------------------------------------------------------------------
# Loop through stations and get frequency responses for each stream
# ---------------------------------------------------------------------
# Pre-filter bandpass corner freqs
# eliminates end frequency spikes (H(t) = F(t)/G(t))
# G(t) != 0
stationName = []	# station names for output plots
for i in range(streamlen):	
	# NOTE: Need a way to scp multiple files using station IDS
	# store resfilenames in a list. Alternate way is scp entire
	# response dir from aslres01
	resfilename = "RESP."+networkID[i]+"."+stationID[i]+"."+locationID[i]+"."+channelID[i]	# response filename
	stationName.append(resfilename)	
	resfile = resppath + resfilename
	os.chdir(resppath)
	cwd = os.getcwd()
	#os.system("scp agonzales@aslres01.cr.usgs.gov:" + resfile + " " + cwd)
	#resp = evalresp(1, nfft, resfilename, t, station=stationID, channel=channelID, network=networkID, locid=locationID, units="DIS", debug=False)
	print "stream[%d]" % i
	print "number of traces = " + str(len(stream[i]))	
	print "datetimeUTC = " + str(datetimeUTC)	
	print "resfilename = " + str(resfilename)
	resp = {'filename': resfilename, 'date': datetimeUTC, 'units': 'DIS'}

	# ------------------------------------------------------------------
	# Simulation/filter for deconvolution
	# NOTE: Filter will be chosen by user, this includes
	# filter coefficients and frequency ranges. Currently all stations	
	# run the same filter design, this will change depending on the 
	# network and data extracted from each station
	# ------------------------------------------------------------------	
	if filtertype == "bandpass":
		stream[i].simulate(paz_remove=None, pre_filt=(c1, c2, c3, c4), seedresp=resp, taper='True')	# deconvolution
		#stream[i].filter(filtertype, freqmin=bplowerfreq, freqmax=bpupperfreq, corners=2)	# bandpass filter design
	elif filtertype == "lowpass":
		stream[i].simulate(paz_remove=None, pre_filt=(c1, c2, c3, c4), seedresp=resp, taper='True')	# deconvolution
		stream[i].filter(filtertype, freq=lpfreq, corners=1)	# lowpass filter design 
	elif filtertype == "highpass":
		stream[i].simulate(paz_remove=None, pre_filt=(c1, c2, c3, c4), seedresp=resp, taper='True')	# deconvolution
		stream[i].filter(filtertype, freq=hpfreq, corners=1)	# highpass filter design
	print "\n"

# ----------------------------------------------------------------
# Magnification (will also support user input)
# ----------------------------------------------------------------
streamlen = len(stream)
for i in range(streamlen):
	index = str(i)	
	strsel = stream[i]	# stream selection
	tracelen = len(strsel)	# number of traces in stream
	if tracelen == 1:
		datalen = len(trace[index].data)
		j = 0	
		for j in range(datalen):	# multiple data points in trace
			trace[index].data[j] = trace[index].data[j] * magnification	# magnitude cal	

	else:
		j = 0	
		for j in range(tracelen):
			tr = trace[index]	# store multiple traces in a tmp trace list
			datalen = len(tr[j])	# number of traces in tmp trace list
			for k in range(datalen):
				tr[j].data[k] = tr[j].data[k] * magnification	# magnitude cal

# ----------------------------------------------------------------
# Plot displacement data
# ----------------------------------------------------------------
os.chdir(plotspath)
for i in range(streamlen):
	stream[i].merge(method=1)
	stream[i].plot(type='dayplot', interval=60, right_vertical_labels=False,
		number_of_ticks=7, one_tick_per_line=True, color=['k', 'r', 'b', 'g'],
		show_y_UTC_label=False, outfile=stationName[i]+".png") 
	#os.remove(resfilename)	# remove response file after computing response
