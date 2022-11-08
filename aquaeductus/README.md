Aquaeductus
===========
Who'd have known that balcony gardening would become the most valuable skill in the new world? Long gone are the times of supermarkets and industrial food processing. Now small greenhouses ornate every building, pulsating with the lights of the machines that control them - optimizing every precious drop of water, and every ray of the pale sun that filters through the pollution. Skilled gardeners are the new rockstars, touring across the communes to tend on their vegetable patches, communing with the AIs that forecast the ever-worsening weather. Be sure to be the first to book them.

Description
-----------
This service manages futuristic gardens where AI predict growth based on weather forecasts, and users can insert their own gardens, and apply and accept requests to water them.

Flags are stored as private information of the admin's garden, and as a comment at the end of the admin's weather report files.


Vulnerabilities
---------------
The service has two flagstores:
- Flagstore 1 - Third line of the admin's weather report files
- Flagstore 2 - Watering instructions of the admin's garden

### Flagstore 1 - Vuln 1
`WeatherLayer` does not check that the number of requested nodes is at most the number of floats that make up a weather report.
By asking for a number of nodes greater than the number of floats there are, a user can also read the flag as input to their neural network.

### Flagstore 1 - Vuln 2
`WeatherLayer` allows for special types of activation functions that take a parameter, besides the input. 
These parameters can be provided in the second line of a weather report (as a list of floats) but are _optional_.
However, there is no check when asking for such activation function that the file contains these parameters as second line.
This means you read characters of the flag as floats, and use them as parameters for the `explu` layer, where they multiply the floats of the first line of the weather report. This might be exploitable.

### Flagstore 2 - Vuln 1
`WateringController.Approve` is checking the garden ownership, but it is not fetching the watering request from the garden.

### Flagstore 2 - Vuln 2
`WeatherLayer` allows to specify arbitrary golang attributes for navigation, included `Garden.Instructions`.
This might eventually give you access to more application data if abused enough.

### Flagstore 2 - Vuln 3
`LocationLayer` allows to retrieve arbitrary properties from the garden model, included `Garden.Instructions`.
Property value is lost during float parsing, but logs output the flag in hex.


Patches
-------

### Flagstore 1 - Patch 1
Validate the input size in wasm (look for new line) or filter out the extra data in golang.

### Flagstore 1 - Patch 2
Check if the second line is empty or not when asked for a layer with parameters.

### Flagstore 2 - Patch 1
`WateringController.Approve` must verify request garden matches input garden.

### Flagstore 2 - Patch 2
Limit `rpcRetrieve` to `ReportData`.

### Flagstore 2 - Patch 3
Remove `console.log` from `ParseFloat`.
