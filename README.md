# Kiosk server for KioskDashboard plugin for labsmanager


### configuration 
rename or copy config_template.json to config.json

##### parameters
 * api_url: url of labsmanager instance, and sub url of kiosk plugin
 * token : a token generated for a user for this request
 * carousel : parameters for carousel management
   * duration : default slide duration (in second)
   * show_title : default behavior to show slide titles (overriden by kiosk plugin parameters)
   * loop : wrap condition of bootstrap carousel
   * reload_interval : interval to reload page from labsmanager (in minute)
 * active_hours : active hours of the kiosk : set start and end hours, outside it will turn of the screen and the server