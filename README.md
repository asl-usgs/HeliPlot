HeliPlot
========
Program execution order
===========================================================

      NOTE: For special circumstances involving only a few user defined stations 
      (i.e. user wants data only from ANMO and BJT). The steps are as follows:
      
      1) Skip steps (1-3)
      2) Edit station.cfg
            * Remove undesired stations
            * Edit filter designs
            * Edit exception lists
      3) Run steps (4-5) for the heli plots and html file

Main order of programs
      
      1) Edit prestation.cfg
            a) Set defualt variables (magnification, resolution, vertical range, etc.)
            b) Set system paths (paths are dependent on the host)
                  * getmetadata: exutable contained in HeliPlot/ directory
                  * datalesspath: dataless seed path unique to server
                  * cwbquery: executable, needs to be installed on server
                  * resppath: frequency response path unique to server
                  * seedpath: temp seed path in HeliPlot/ directory
                  * plotspath: tmp heli plots path in HeliPlot/ directory
                  * gifconvert: executable contained in HeliPlot/ directory
                  * nodata: gif image contained in HeliPlot/ directory
                  * helihtmlpath: tmp html path in HeliPlot/ directory
            c) Set filter designs (unique to channel ID)
            d) Set exception lists
                  * rmnetwork: remove specified networks
                  * channelexc: change channelIDs for specified station(s) (default is LHZ)
                  * locationexc: change locationIDs for specified station(s) (default is 00)
                  * magnificationexc: change magnitude for specified station(s) (default is 3000.0)
                  
      2) Run stationNames.py (./stationNames.py)
            a) Descrip: Calls getMetadata.py to pull metadata from operable stations
            b) Inputs:  prestation.cfg
            c) Outputs: stationNames.txt (station names to be used in readStations.py)
            
      3) Run readStations.py (./readStations.py)
            a) Descrip: Reads station config/names and creates/populates a main config file for HeliPlot.py
            b) Inputs:  prestation.cfg
                        stationNames.txt
            c) Outputs: station.cfg
            
      4) Run HeliPlot.py (./HeliPlot.py)
            a) Descrip: Reads station.cfg and creates heli plots for each station, if station 
                        contains no data we will use nodata.gif as output plot
            b) Inputs:  station.cfg
            c) Outputs: OutputPlots/*.png heli plots for each station in stationNames.txt
            
      5) Run run_heli_24hr.py (./run_heli_24hr.py)
            a) Descrip: Pulls *.png files from OutputPlots/ and creates *.html files for each image
            b) Inputs:  prestation.cfg (needed for paths)
                        stationNames.txt
                        OutputPlots/*.png
            c) Ouptuts: HeliHTML/*.html
===========================================================
