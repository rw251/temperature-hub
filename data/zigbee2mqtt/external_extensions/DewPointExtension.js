class DewPointExtension {
    constructor(zigbee, mqtt, state, publishEntityState, eventBus, enableDisableExtension, restartCallback, addExtension, settings, logger) {
	this.zigbee = zigbee;
        this.mqtt = mqtt;
        this.state = state;
        this.publishEntityState = publishEntityState;
        this.eventBus = eventBus;
        this.settings = settings;
        this.logger = logger;

        this.onStateChange = this.onStateChange.bind(this); // so that onstatechange can access this

        this.eventBus.onStateChange(this, this.onStateChange);

        logger.info('Loaded DewPointExtension');
    }
  
    /**
     * This method is called by the controller once Zigbee2MQTT has been started.
     */
    start() {
        this.mqtt.publish('dewpoint', JSON.stringify({"message":"hello", "status":"OK"}));
    }

    async onStateChange(data){
      console.log('STATE CHANGE');
      try{
        let thisDevice;
        for (const device of this.zigbee.devicesIterator((d) => d.type !== 'GreenPower')) {
          if (device.options.disabled) {
              continue;
          }
          if(data.entity.zh._ieeeAddr === device.zh.ieeeAddr){
            thisDevice = device;
          }
        }
        if(thisDevice && data.to && data.to.temperature && data.to.humidity) {
          const {temperature, humidity, battery, voltage} = data.to;
          const dewPoint = (1/((1/273) - Math.log((0.611 * Math.exp(5423 * ((1/273) - (1/(273+temperature)))))*humidity/61.1)/5423)) - 273;
          const device = {
            ieeeAddr: thisDevice.ieeeAddr,
            friendlyName: thisDevice.name,
            type: thisDevice.zh.type,
            networkAddress: thisDevice.zh.networkAddress,
            manufacturerName: thisDevice.zh.manufacturerName,
            modelID: thisDevice.zh.modelID,
          }
          this.mqtt.publish('dewpoint/' + device.friendlyName, JSON.stringify({device, voltage, battery, temperature, humidity, dewPoint}), {retain: true, qos: 2});
        }
      } catch(e) {
        console.log('ERROR', e);
      }
    }

    /**
     * Is called once the extension has to stop
     */
    stop() {
        this.eventBus.removeListeners(this);
    }
}

module.exports = DewPointExtension;
