var express = require('express');
var app = express();
var http = require('http').Server(app);
var io = require('socket.io')(http);
var utf8 = require('utf8');
const fs = require('fs');

app.use(express.static('/home/pi/nodeapps/intercom/static'));

app.get('/', function(req, res){
  res.sendFile('index.html',  { root: __dirname });
});
app.get('/config', function(req, res){
  res.sendFile('config.html',  { root: __dirname });
});
// CONFIGURE YOUR DEVICES
var devices = {
  "icbp1": {channels:1, ch1:"-", ch2:"-", ch3:"-", ch4:"-", ch5:"-", ch6:"-", ch7:"-", ch8:"-", role:"-", state:"-", sigquality:"-", siglevel:"-"},
  "icbp2": {channels:1, ch1:"-", ch2:"-", ch3:"-", ch4:"-", ch5:"-", ch6:"-", ch7:"-", ch8:"-", role:"-", state:"-", sigquality:"-", siglevel:"-"},
  "icbp3": {channels:1, ch1:"-", ch2:"-", ch3:"-", ch4:"-", ch5:"-", ch6:"-", ch7:"-", ch8:"-", role:"-", state:"-", sigquality:"-", siglevel:"-"},
  "icbs1": {channels:1, ch1:"-", ch2:"-", ch3:"-", ch4:"-", ch5:"-", ch6:"-", ch7:"-", ch8:"-", role:"-", state:"-", sigquality:"-", siglevel:"-"}
};
// CONFIGURE YOUR ROLES
var roles = {
  "CAMS": {desc:"ALL CAMERAS",talksto:"NOT TALKING"},
  "CAM1": {desc:"CAMERA 1",talksto:"NOT TALKING"},
  "CAM2": {desc:"CAMERA 2",talksto:"NOT TALKING"},
  "DIR": {desc:"DIRECTOR BASESTATION",talksto:"NOT TALKING"},
  "[VIDEO]": {desc:"VIDEO CHANNEL + SUB CHANNELS",talksto:"NOT TALKING"}
}
// SETUP MQTT CONNECTION
var mqtt = require('mqtt');
var connectOptions = {
    host: "192.168.10.125",
    port: 8883,
    protocol: "mqtts",
    keepalive: 10,
    clientId: "nodeIntercom" + Math.random().toString(16).substr(2, 8),
    protocolId: "MQTT",
    protocolVersion: 4,
    clean: true,
    username: "intercom",
    password: "_Interc0M_",
    reconnectPeriod: 2000,
    connectTimeout: 2000,
    rejectUnauthorized: false
};

// DO NOT MAKE CHANGES BELOW UNLESS YOU KNOW WHAT YOU ARE DOING
var client = mqtt.connect(connectOptions);

client.on('connect', function () {
  client.subscribe('media/intercom/#');
  console.log('Connected to MQTT server');
});

client.on('message', function (topic, message) {
  for (i = 0; i < Object.keys(devices).length; i++) {
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/deviceChannels") {
        devices[Object.keys(devices)[i]]["channels"] = parseInt(message);
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/deviceRole") {
        if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["role"] = message.toString();
        } else {
	  devices[Object.keys(devices)[i]]["role"] = "-";
        }
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/state") {
        devices[Object.keys(devices)[i]]["state"] = message.toString();
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/channel/1") {
	if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["ch1"] = message.toString();
	} else {
	  devices[Object.keys(devices)[i]]["ch1"] = "-";
	}
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/channel/2") {
	if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["ch2"] = message.toString();
	} else {
	  devices[Object.keys(devices)[i]]["ch2"] = "-";
	}
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/channel/3") {
	if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["ch3"] = message.toString();
	} else {
	  devices[Object.keys(devices)[i]]["ch3"] = "-";
	}
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/channel/4") {
	if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["ch4"] = message.toString();
	} else {
	  devices[Object.keys(devices)[i]]["ch4"] = "-";
	}
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/channel/5") {
	if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["ch5"] = message.toString();
	} else {
	  devices[Object.keys(devices)[i]]["ch5"] = "-";
	}
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/channel/6") {
	if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["ch6"] = message.toString();
	} else {
	  devices[Object.keys(devices)[i]]["ch6"] = "-";
	}
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/channel/7") {
	if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["ch7"] = message.toString();
	} else {
	  devices[Object.keys(devices)[i]]["ch7"] = "-";
	}
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/channel/8") {
	if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["ch8"] = message.toString();
	} else {
	  devices[Object.keys(devices)[i]]["ch8"] = "-";
	}
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/linkQuality") {
	if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["sigquality"] = message.toString();
	} else {
	  devices[Object.keys(devices)[i]]["sigquality"] = "-";
	}
      }
      if (topic.toString() == "media/intercom/status/" + Object.keys(devices)[i] + "/signalLevel") {
	if (message.toString().trim() != "") {
          devices[Object.keys(devices)[i]]["siglevel"] = message.toString();
	} else {
	  devices[Object.keys(devices)[i]]["siglevel"] = "-";
	}
      }
  }
  for (i = 0; i < Object.keys(roles).length; i++) {
    if (topic.toString() == "media/intercom/broadcast/" + Object.keys(roles)[i] + "/talk") {
      roles[Object.keys(roles)[i]]["talksto"] = message.toString();
    }
  }
});

function checkTime(i) {
    if (i < 10) {i = "0" + i};
    return i;
}

setInterval(function() {
  var today = new Date();
  var h = today.getHours();
  var m = today.getMinutes();
  var s = today.getSeconds();
  h = checkTime(h);
  m = checkTime(m);
  s = checkTime(s);
  clock = h + ':' + m + ':' + s;
  io.emit('intercomData', { clock : clock, devices : devices, roles: roles });
}, 250);

io.on('connection', function(socket){
  socket.on('updateDevice', function(deviceName, role, channelData, callback){
    // CHECK IF DEVICE EXISTS
    if (deviceName in devices) {
      // CHECK IF ROLE EXISTS
      if (role in roles) {
        // UPDATE ROLE
        client.publish("media/intercom/setup/" + deviceName + "/deviceRole", role, {qos: 0, retain: true});
      }
      if (channelData.length == devices[deviceName]["channels"]) {
        for (var i = 0; i < channelData.length; i++ ) {
          client.publish("media/intercom/setup/" + deviceName + "/channel/" + (i+1), channelData[i].join(), {qos: 0, retain: true}); 
        }
      }
      callback('200');
    }
  });
});

http.listen(3000, function(){
  console.log('listening on *:3000');
});
