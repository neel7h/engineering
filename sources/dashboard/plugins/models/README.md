# Models quick documentation

The models plugin represent a specific and sensitive part of the application. The plugin provide base implementations 
for models and collection (relying on backbone 1.1.x version and underscore 1.6). 

The plugin is made of multiple files that are compiled in a single one. If you add a new file component to the plugin,
please keep in mind that you need to update the Gruntfile.js at the project source to include this file with adequate 
order.

* models.js is made of:
    * models.coffee defining the root model components and aggregating the facade exposed by the plugin
    * applications.coffee that provides models and collections related to applications listing or details
    * users.coffee that provides models to interact with data related to the user
    * results.coffee that provides models related to results exploration
    
