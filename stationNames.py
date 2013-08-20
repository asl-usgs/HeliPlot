import os
dirlist = os.listdir('/xs0/seed')
dirlist.sort()
fin = open('stationNames.txt', 'w')
listlen = len(dirlist)
for i in range(listlen):
	fin.write(dirlist[i])
	fin.write("\n")
fin.close
