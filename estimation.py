# -*- coding: utf-8 -*-
"""
Created on Sat Sep 15 15:33:15 2018

@author: mujee
"""

from uber_rides.session import Session
from uber_rides.client import UberRidesClient
import googlemaps
import math
import requests
import googlemaps
import pandas as pd
import gurobipy as grb

googleapi="AIzaSyCj-tVQHaVsnIs53U2PlzgzhQZUmxFWmGU"
uberapi="vENI7dPMGJ48pTH4qiMZQJzbKx-P6i8t4QL2dndR"

gmaps=googlemaps.Client(key=googleapi)

session = Session(server_token=uberapi)
client = UberRidesClient(session)
    
def main(origin, points, time):
    cols=['orig','dest','orig_ll','dest_ll','distance','speed']
    #getting lat, long of all the points
    latlng_o=getlatlng(origin)
    latlng_d=getlatlng(points[-1])
    latlng_p=[]
    for places in points[:-1]:
        latlng_p.append(getlatlng(places))
    if len(points)==0: return 'no destination'
    if len(points)==1: return 'go from '+origin+' to '+points[0]
    #calculating distance and speed of all the feasible Origin-destination pairs
    if len(points)>1:
        matrix=[]
        for i in range(len(points[:-1])):
            matrix.append([origin, points[i], latlng_o,latlng_p[i], getdistance(latlng_o,latlng_p[i]),getspeed(latlng_o,time)])
            matrix.append([points[i], points[-1],latlng_p[i],latlng_d, getdistance(latlng_p[i],latlng_d),getspeed(latlng_p[i],time)])
            for j in range(len(points[:-1])):
                if i==j: continue
                matrix.append([points[i],points[j],latlng_p[i],latlng_p[j], getdistance(latlng_p[i],latlng_p[j]),getspeed(latlng_p[i],time)])
    df=pd.DataFrame(matrix,columns=cols)
    df[['distance','speed']]=df[['distance','speed']].astype(float)
    df['ttime']=df['distance']*df['speed']
    #calculating the optimal route by minimizing travel time
    route=optimize(df,latlng_o,latlng_d,latlng_p)
    #calculating uber price estimate of optimal path
    output=uberestimate(route)
    
    order=pd.Series(index=range(len(route)+1), data=list(route['orig'])+[list(route['dest'])[-1]], name='points')
    #output is order of points and uber cost estimates by all available vehicle types
    return order, "        ", output

def getlatlng(address):
    global googleapi
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json?address={}".format(address)
    geocode_url = geocode_url + "&key={}".format(googleapi)
    output = requests.get(geocode_url)
    output = output.json()['results'][0]
    lat=round(output.get('geometry').get('location').get('lat'),5)
    lng=round(output.get('geometry').get('location').get('lng'),5)
    return (lat,lng)

def getdistance(orig, dest):
    mydistance=gmaps.distance_matrix(orig,dest)
    a=mydistance[u'rows'][0][u'elements'][0][u'duration'][u'text'].encode('ascii','ignore')
    tt=a[:a.find(" ")]+":"+a[a.find(" ",a.find(" ")+2)+1:a.find(" ",a.find(" ")+2)+3]
    distance=mydistance[u'rows'][0][u'elements'][0][u'distance'][u'text'].encode('ascii','ignore')[:-3]
    return distance

def getspeed(latlng,time):
    time=(float(60*(time-time%100)/100+time%100)/(24*60))
    sum_latlng=(round((latlng[0]%int(latlng[1]))*3600)%60+round((latlng[0]%int(latlng[1]))*3600)%60)
    cong=sum_latlng*(time+.1)
    speed=max(5,100-(cong))
    return speed

def optimize(df,latlng_o,latlng_d,latlng_p):

    orig=list(df["orig_ll"])
    dest=list(df["dest_ll"])
    ttime=list(df["ttime"])
    allpoints=[latlng_o]+latlng_p+[latlng_d]
    S={}
    for i in range(len(orig)):
        S[(orig[i],dest[i])]=ttime[i]
    #model m initialization
    m=grb.Model()
    #variable definition
    x={}
    for i in S:
        x[i]=m.addVar(vtype=grb.GRB.BINARY, name="%(1)s" % {'1':i})
    #origin constraint
    m.addConstr(grb.quicksum(x[(latlng_o,i)] for i in latlng_p) ==1)
    #destination constraint
    m.addConstr(grb.quicksum(x[(i,latlng_d)] for i in latlng_p) ==1)
    # number of transit points constraints
    for i in latlng_p:
        m.addConstr((grb.quicksum(x[(i,j)] for j in allpoints if (i,j) in S)+grb.quicksum(x[(j,i)] for j in allpoints if (j,i) in S)) ==2)
    #objective function definition
    m.setObjective(grb.quicksum(S[i]*x[i] for i in S), grb.GRB.MINIMIZE)
    m.update()
    m.optimize()
    #model optimized
    output=[str(m.getVars()[i]) for i in range(len(m.x)) if m.x[i]==1]
    df['x']=0
    for i in range(len(df)):
        for j in output:
            if str(df["orig_ll"].iloc[i]) in j[:40] and str(df["dest_ll"].iloc[i]) in j[22:]:
                df.loc[i,'x']=1
    #only optimal route which is part of solution
    route=df[df.x==1]
    #order of the route
    route.loc[route['orig']==origin,'order']=0
    for i in range(1,len(route)):
        route.loc[route['orig']==route['dest'].loc[route['order']==route['order'].max()].tolist()[0],'order']=i
    route.index=route.order
    return route

def uberestimate(route):
    for i in range(len(route)):
        response = client.get_price_estimates(
                start_latitude=route['orig_ll'].iloc[i][0],
                start_longitude=route['orig_ll'].iloc[i][1],
                end_latitude=route['dest_ll'].iloc[i][0],
                end_longitude=route['dest_ll'].iloc[i][1],
                seat_count=1)
        estimate = response.json.get('prices')
        temp=a=pd.DataFrame(estimate)
        temp['orig']=route['orig'].iloc[i]
        temp['dest']=route['dest'].iloc[i]
        if i==0:
            result=temp
        else:
            result=result.append(temp, ignore_index=True, sort=False)
    #surge price discounting and getting price averaging the low and higher estimate
    result['price']=(result['high_estimate']+result['low_estimate'])/(2*result['surge_multiplier'])
    s=result.groupby(['display_name'])['price'].sum()
    output=pd.DataFrame({'type':s.index, 'cost':s.values})
    output['count']=list(result.groupby(['display_name'])['price'].count())
    #removing the vehicle types which are not available on all route combinations
    output=output[output["count"]==len(route)]
    output=pd.Series(index=output.type, data=list(output.cost), name='cost')

    return output
