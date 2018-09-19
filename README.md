# uberestimate
The code has been commented on extensively to follow it easily. The following functions were used to get the desired output.
# getlatlng
Takes an address in plain english as input, and return latitude and longitude of that address, using googlemaps api
#getdistance
Takes origin and destination (lat,lng) pairs as input, and return the distance between the two points, using googlemaps api
# getspeed
Takes time and (lat,lng) pair as input, and return the speed
# optimize
Takes a dataframe containing all the feasible origin-destination pairs as input, and return the optimal origin-destination pairs as output
# uberestimate
takes the optimal combinations with minimum travel time as input, and return the price estimate of all the trips
# main
This function takes origin (string), transit points (list of all the points, with destination as last point) and start time (integer e.g. 1100) as input, and using the above functions give the estimate of the trip
# example input
origin = 'lums lahore'
points=['lalik chowk lahore', 'general hospital lahore', 'kalma chowk lahore', 'daewoo terminal lahore']
time=1100
main(origin,points,time)
