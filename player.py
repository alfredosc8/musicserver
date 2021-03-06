import pygst, gst, logging, gobject, threading, beatcontrol, requests, re

gobject.threads_init()

class Player:
	pipeline = None
	current = None
	beatcontrol = None

	def __init__(self, beatcontrol):
		self.beatcontrol = beatcontrol
		g_loop = threading.Thread(target=gobject.MainLoop().run)
		g_loop.daemon = True
		g_loop.start()
		print "Initialized player and started gst daemon thread"

	def play(self, url):
		logging.debug('Playing ' + url)
		self.pause()
		self.create_pipeline(url)
		self.current = url;
		self.beatcontrol.start()
		self.pipeline.set_state(gst.STATE_PLAYING)

	def pause(self):
		logging.debug('Pausing')
		self.beatcontrol.stop()
		if (self.pipeline is not None):
			self.pipeline.set_state(gst.STATE_PAUSED)

	def togglePlayPause(self):
		if (self.is_playing()):
			print "toggling to pause"
			self.pause()
		elif (self.is_paused() and self.current is not None):
			print "toggling to play"
			self.play(self.current)

	def setVolume(self, volume):
		if (self.pipeline is not None):
			self.pipeline.get_by_name("volume").set_property("volume", volume)

	def setTreble(self, level):
		if (self.pipeline is not None):
			self.pipeline.get_by_name("equalizer").set_property("band2", level)

	def setBass(self, level):
		if (self.pipeline is not None):
			self.pipeline.get_by_name("equalizer").set_property("band0", level)


	def is_paused(self):
		return self.pipeline is not None and gst.STATE_PAUSED in self.pipeline.get_state(timeout=1)

	def is_playing(self):
		if (self.pipeline is None):
			return False;
		states = self.pipeline.get_state(timeout=1)
		return gst.STATE_PLAYING in states and gst.STATE_PAUSED not in states

	def handle_level_messages(self, bus, message):
		if (message.structure is not None and message.structure.get_name() == 'level'):
			self.beatcontrol.handle_level_message(message)

	def create_pipeline(self, url):
		try:
			if (self.pipeline is not None):
				self.pipeline.set_state(gst.STATE_NULL)
	
			source = 'souphttpsrc' if url.startswith('http') else 'filesrc';
			url = self.parse_playlist(url) if source == 'souphttpsrc' and '.pls' in url else url;
			thePipeline = source + ' location="' + url + '" ! mad ! tee name=t ! queue ! audioconvert ! audiocheblimit mode=low-pass cutoff=40 type=1 ! level interval=16000000 ! fakesink t. ! queue ! audioconvert ! equalizer-3bands name=equalizer ! volume name=volume ! alsasink'
			logging.debug(thePipeline)
	
			self.pipeline = gst.parse_launch(thePipeline)
	
			# Connect this player to the gstreamer bus
			bus = self.pipeline.get_bus()
			bus.add_signal_watch()
			bus.connect('message', self.handle_level_messages)
		except Exception as e:
			print e
			pass

	def parse_playlist(self, url):
		return re.search('File.=(.*)', requests.get(url).text).group(1)


