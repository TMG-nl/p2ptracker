# Introduction

# Configfile

# Redis storage model

We use redis to store tracker information in including transfer stats for any
running transfers.

racks = all racks we've seen  
rack:<rackname> = all hosts we've ever seen in this rack  

transfers = all seen info_hashes  
active_transfers = all active info_hashes  

<hash>:peers:N =  all seen peers for the hash  
<hash>:peers:R =  all representants for the hash  
<hash>:peers:S =  all seeders for the hash  
<hash>:peers:L =  all leechers for the hash  

<hash>:rack:<rackname>:N =  all peers for the hash in a rack  
<hash>:rack:<rackname>:R =  all repr for the hash in a rack  
<hash>:rack:<rackname>:S =  all seeders for the hash in a rack  

<hash>:peer:<peeripaddress>:compact = True/False  
<hash>:peer:<peeripaddress>:port = port where the client is operating on  
<hash>:peer:<peeripaddress>:peer_id = peer id from client  
<hash>:peer:<peeripaddress>:key = peer key  
<hash>:peer:<peeripaddress>:last_event = last seen event  
<hash>:peer:<peeripaddress>:event:<event> = datetime event was seen  
<hash>:peer:<peeripaddress>:seeder = True/False  
<hash>:peer:<peeripaddress>:downloaded = bytes downloaded  
<hash>:peer:<peeripaddress>:left = bytes left to downlaod  
<hash>:peer:<peeripaddress>:uploaded = bytes uploaded to other clients  
<hash>:peer:<peeripaddress>:rack = rack where the peer is located  
<hash>:peer:<peeripaddress>:hostname = hostname reported for ipaddress  

<hash>:length = length of the torrent payload  
<hash>:name = name of the torrent  
<hash>:registered = datetime transfer was activated  
<hash>:deregistered = datetime transfer was deactivated  
<hash>:first_started = datetime first peer started downloading  
<hash>:last_started = datetime last peer started downloading  
<hash>:first_completed = datetime first peer completed downloading  
<hash>:last_completed = datetime last peer completed downloading  

peer = ipaddress:port of the peer  
rack = rackname  
hash = uppercase hash for the torrent  

ALL VALUES ARE STRINGS !!!!!!

Deactivation renames all keys that start with <hash>, to <datetime>:<hash> where <datetime> is the datetime of deactivation
