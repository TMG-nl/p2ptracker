# TODO list

* Fix the hash test

For some stupid reason the transfer hash testcase will not succeed :(
I probably lack sufficient knowledge and patience to figure out what is going wrong with the different charsets involved

* Add compliant scrape support: http://wiki.theory.org/BitTorrentSpecification#Tracker_.27scrape.27_Convention

Replace current statistics interface with it

* Add / Test multiple tracker support against a single redis backend

Better scalability, yeah

* Add scripts to generate torrents and push them to the tracker / seeders

Nicer for other people working with this

* Add generic multi level swarm support

It should be possible to do multi-level swarms fairly easy, we have not yet found a use for that
But larger shops might want to resort to something along the lines of a Global-Swarm -> DC-Swarm -> Rack-Swarm

* Add plugin system for group classifiers

The current group classifier for nodes is crude and tied to our specific implementation of a metadata service for nodes
in our environment. Reimplementing this as a plugin system would make it more usable for others and allow easy
development of plugins.
