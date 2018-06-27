### Local Repo Structure

The GTFS Data is too big to be local, so set up your project tree as shown below. Note that you will need to create two directories for Data and Results (e.g., saving graphs and their associated data):

```
Project/
|
|--- Data/
|	  |
|	  |--- madrid_metro/
|	  |
|	  |--- caltrain/
|	  |
|	  |--- nyc_subway/
|	  |
|	  |--- ...
|
|
|--- Results/
|
|--- Source/ <--- clone the main Me0w repo here!
```


### Source Code Structure

Our source code is organized as follows:

```
README.md <--- This file.
|
DjangoSite/
|
|--- DjangoSite/ <--- Django settings.
|	  |
|	  |--- ...
|
|
|--- snapData/
|	  |
|	  |--- (Assorted Django files for handling URL mappings, views, form submissions, and the model.)
|	  |
|	  |--- Backend/ <--- Python scripts for creating SNAP networks, calculating criticality, and computing isochrones.
|	  |    |
|	  |    |--- ...
|	  |
|	  |--- templates/ <--- HTML templates for the application.
|	  |    |
|	  |    |--- ...
```