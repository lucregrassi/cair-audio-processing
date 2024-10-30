# Audio acquisition from the microphone
This repository contains files that should be stored on the platform used as a microphone (it can also be the same one used for the CAIR client).
The scripts in this repository connect to Microsoft APIs to perform Speech Recognition and Speaker Recognition. 
The audio can be recorded in different languages, however, the server currently supports only English (default) and Italian (launch the script with the argument -l it).

* The *audio_recorder* script starts listening when signaled by the client and starts registering when noise above a defined threshold is heard. The registration stops after a silence of a pre-defined number of seconds. The WAV file containing the recorded audio is then sent to Microsoft Speech Recognition API. If something is recognized, in the multiparty mode, it is also sent to Microsoft Speaker Recognition API to perform Speaker Identification (only if at least one profile is enrolled). The result of this procedure generates an XML string with the transcribed speech tagged with the profile IDs of the recognized speakers (if any), which is returned to the client. 
* The *registration.py* script is in charge of performing the registration of a new speaker. When the client detects that the Plan Manager service has matched the intent for the registration, it writes into the socket to start the registration. The steps for the registration are the following: 
  * Creation of a new profile ID
  * Acquisition of user name
  * Profile enrollment (the user is asked to talk for 20 seconds)
  * Acquisition of initial state for the new user (performing a request to the Hub)
  * Update of the information of the speakers and the statistics
  
Once the registration is completed, the client continues the dialogue by saying the starting sentence of the dialogue with the new user and returns to listen thanks to the *audio_recorder* service.

