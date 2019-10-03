(function() {
  var Bus, Core, Facade, bootstrap, checkType, plug, plugins, stem, _,
      __slice = [].slice;

  Bus = (function() {
    function Bus() {
      this.channels = {};
    }

    Bus.prototype.on = function(channel, callback, context) {
      var id, subscription, that, _base, _i, _j, _len, _len1, _ref, _results, _results1;
      if (context == null) {
        context = this;
      }
      if (channel instanceof Array) {
        if (typeof callback !== "function") {
          return false;
        }
        _results = [];
        for (_i = 0, _len = channel.length; _i < _len; _i++) {
          id = channel[_i];
          _results.push(this.on(id, callback, context));
        }
        return _results;
      } else if (typeof channel === "object") {
        if (Bus._isEmpty(channel)) {
          return false;
        }
        _results1 = [];
        for (id in channel) {
          _results1.push(this.on(id, channel[id], callback || context));
        }
        return _results1;
      } else {
        if (typeof channel !== "string") {
          return false;
        }
        if (typeof callback !== "function") {
          return false;
        }
        if ((_base = this.channels)[channel] == null) {
          _base[channel] = [];
        }
        that = this;
        _ref = this.channels[channel];
        for (_j = 0, _len1 = _ref.length; _j < _len1; _j++) {
          subscription = _ref[_j];
          if (subscription.callback === callback && subscription.context === context) {
            return false;
          }
        }
        subscription = {
          context: context,
          callback: callback
        };
        return {
          attach: function() {
            if (!(that.channels[channel].indexOf(subscription) > -1)) {
              that.channels[channel].push(subscription);
            }
            return this;
          },
          detach: function() {
            Bus._remove(that, channel, subscription.callback, void 0);
            return this;
          }
        }.attach();
      }
    };

    Bus.prototype.off = function(channel, callback) {
      var id;
      switch (typeof channel) {
        case 'string':
          if (typeof callback === 'function') {
            Bus._remove(this, channel, callback, void 0);
          }
          if (typeof callback === 'undefined') {
            Bus._remove(this, channel, void 0, void 0);
          }
          break;
        case 'function':
          for (id in this.channels) {
            Bus._remove(this, id, channel, void 0);
          }
          break;
        case 'object':
          for (id in channel) {
            Bus._remove(this, id, channel[id], void 0);
          }
      }
      return this;
    };

    Bus.prototype.emit = function(channel, data, callback) {
      var subscriber, subscribers, tasks;
      if (typeof channel !== 'string') {
        return false;
      }
      if (typeof data === 'function') {
        callback = data;
        data = void 0;
      }
      if (callback == null) {
        callback = function() {};
      }
      subscribers = this.channels[channel] || [];
      tasks = (function() {
        var _i, _len, _results;
        _results = [];
        for (_i = 0, _len = subscribers.length; _i < _len; _i++) {
          subscriber = subscribers[_i];
          _results.push((function(subscriber) {
            return function(nextTask) {
              var e;
              try {
                return nextTask(void 0, subscriber.callback.apply(subscriber.context, [data, channel]));
              } catch (_error) {
                e = _error;
                return nextTask(e);
              }
            };
          })(subscriber));
        }
        return _results;
      })();
      Bus._runTasks(tasks, (function(errors, results) {
        var e, x;
        if (errors != null) {
          e = (function() {
            var _i, _len, _results;
            _results = [];
            for (_i = 0, _len = errors.length; _i < _len; _i++) {
              x = errors[_i];
              if (x != null) {
                _results.push(x);
              }
            }
            return _results;
          })();
          console.error(e);
        }
        return callback(e, results);
      }));
      return this;
    };

    Bus._isEmpty = function(object) {
      var key;
      if (object == null) {
        return true;
      }
      if (object.length > 0) {
        return false;
      }
      if (object.length === 0) {
        return true;
      }
      for (key in object) {
        if (object.hasOwnProperty(key)) {
          return false;
        }
      }
      return true;
    };

    Bus._remove = function(object, channel, callback, context) {
      var subscription;
      if (object.channels[channel] == null) {
        return;
      }
      return object.channels[channel] = (function() {
        var _i, _len, _ref, _results;
        _ref = object.channels[channel];
        _results = [];
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          subscription = _ref[_i];
          if ((callback != null ? subscription.callback !== callback : context != null ? subscription.context !== context : subscription.context !== object)) {
            _results.push(subscription);
          }
        }
        return _results;
      })();
    };

    Bus._runTasks = function(tasks, doneCallback) {
      var errors, index, nextTask, results;
      if (tasks == null) {
        tasks = [];
      }
      if (doneCallback == null) {
        doneCallback = (function() {});
      }
      index = -1;
      results = [];
      if (tasks.length === 0) {
        return doneCallback(null);
      }
      errors = null;
      nextTask = function() {
        var e, err, res;
        err = arguments[0], res = 2 <= arguments.length ? __slice.call(arguments, 1) : [];
        if (err) {
          if (errors == null) {
            errors = [];
          }
          errors[index] = err;
        } else {
          if (index > -1) {
            results.push(res.length < 2 ? res[0] : res);
          }
        }
        if (++index >= tasks.length) {
          return doneCallback(errors, results);
        } else {
          try {
            return tasks[index](nextTask);
          } catch (_error) {
            e = _error;
            return nextTask(e);
          }
        }
      };
      return nextTask();
    };

    return Bus;

  })();

  checkType = function(type, val, name) {
    if (typeof val !== type) {
      return "" + name + " has to be a " + type;
    }
  };

  Core = (function() {
    function Core(API) {
      this.modules = {};
      this.plugins = {};
      this.bus = new Bus();
      this.API = API || Facade;
    }

    Core.prototype.log = {
      error: function() {
        var argument, _i, _len, _results;
        _results = [];
        for (_i = 0, _len = arguments.length; _i < _len; _i++) {
          argument = arguments[_i];
          _results.push(typeof console !== "undefined" && console !== null ? console.error(argument) : void 0);
        }
        return _results;
      },
      warn: function() {
        var argument, _i, _len, _results;
        _results = [];
        for (_i = 0, _len = arguments.length; _i < _len; _i++) {
          argument = arguments[_i];
          _results.push(typeof console !== "undefined" && console !== null ? console.error(argument) : void 0);
        }
        return _results;
      },
      log: function() {
        var argument, _i, _len, _results;
        _results = [];
        for (_i = 0, _len = arguments.length; _i < _len; _i++) {
          argument = arguments[_i];
          _results.push(typeof console !== "undefined" && console !== null ? console.log(argument) : void 0);
        }
        return _results;
      },
      info: function() {}
    };

    Core.prototype.register = function(moduleId, module, options) {
      var err;
      if (options == null) {
        options = {};
      }
      err = checkType("string", moduleId, "module ID") || checkType("function", module, "creator") || checkType("object", options, "option parameter");
      if (err) {
        this.log.error("could not register module '" + moduleId + "': " + err);
        return this;
      }
      if (moduleId in this.modules) {
        this.log.warn("module " + moduleId + " is already registered");
        return this;
      }
      this.modules[moduleId] = {
        moduleId: moduleId,
        module: module,
        options: options
      };
      return this;
    };

    Core.prototype.start = function(moduleId, onStarted) {
      var processModule,
          _this = this;
      if (!checkType('function', moduleId, "onStarted")) {
        onStarted = moduleId;
        moduleId = void 0;
      }
      processModule = function(moduleId, initializationStep) {
        var error, module;
        if (initializationStep == null) {
          initializationStep = 'initialize';
        }
        module = _this.modules[moduleId];
        if (module.hasErrors) {
          return;
        }
        try {
          if (module.instance == null) {
            module.api = new _this.API(_this);
            module.instance = new module.module(module.api);
          }
          if ((module.instance[initializationStep] != null) && !module.instance[initializationStep].processed) {
            module.instance[initializationStep](module.options);
            return module.instance[initializationStep].processed = true;
          }
        } catch (_error) {
          error = _error;
          delete module.instance;
          module.hasErrors = true;
          return _this.log.error(("module " + moduleId + " failed to ") + initializationStep, error);
        }
      };
      if (moduleId != null) {
        processModule(moduleId, 'initialize');
        processModule(moduleId, 'postInitialize');
        if (typeof onStarted === "function") {
          onStarted();
        }
        return;
      }
      for (moduleId in this.modules) {
        processModule(moduleId, 'initialize');
      }
      for (moduleId in this.modules) {
        processModule(moduleId, 'postInitialize');
      }
      return typeof onStarted === "function" ? onStarted() : void 0;
    };

    Core.prototype.stop = function(moduleId, onStop) {
      var processModule,
          _this = this;
      if (!checkType('function', moduleId, "onStop")) {
        onStop = moduleId;
        moduleId = void 0;
      }
      processModule = function(moduleId) {
        var error, module, _base;
        module = _this.modules[moduleId];
        if (module.instance == null) {
          return;
        }
        try {
          if (typeof (_base = module.instance).destroy === "function") {
            _base.destroy();
          }
          module.api.bus.__clear();
          module.api = null;
          return module.instance = null;
        } catch (_error) {
          error = _error;
          return _this.log.error("module " + moduleId + " failed to destroy");
        }
      };
      if (moduleId != null) {
        processModule(moduleId);
        if (typeof onStop === "function") {
          onStop();
        }
        return this;
      }
      for (moduleId in this.modules) {
        processModule(moduleId);
      }
      this.bus.emit('stopped');
      return typeof onStop === "function" ? onStop() : void 0;
    };

    Core.prototype.use = function(plugin) {
      var API, Facade, currentFacade, field, newFacade, previousFacade, subField;
      if (plugin == null) {
        return this.log.warn('no plugin provided to use');
      }
      if (typeof plugin === 'function') {
        plugin = new plugin(this.bus);
      }
      if (plugin.id == null) {
        return this.log.error("plugin invalid, lack of 'id' property", plugin);
      }
      if (this.plugins[plugin.id] != null) {
        return this.log.warn("Plugin " + plugin.id + " already exist", plugin);
      }
      if (plugin.Facade != null) {
        Facade = this.API._.extend({}, plugin.Facade);
        currentFacade = new this.API();
        for (field in Facade) {
          if (currentFacade.hasOwnProperty(field)) {
            previousFacade = currentFacade[field] || {};
            newFacade = plugin.Facade[field];
            for (subField in newFacade) {
              if (previousFacade.hasOwnProperty(subField)) {
                return this.log.error("plugin " + plugin.id + " declares facade attribute " + field + " that is already defined in the current facade");
              }
            }
            Facade[field] = this.API._.extend({}, newFacade, previousFacade);
          }
        }
      }
      this.plugins[plugin.id] = plugin;
      if (Facade != null) {
        API = this.API;
        this.API = this.API.extend({
          initialize: function(moduleManager) {
            var _ref, _results;
            if ((_ref = API.prototype.initialize) != null) {
              _ref.apply(this, arguments);
            }
            _results = [];
            for (field in Facade) {
              _results.push(this[field] = Facade[field]);
            }
            return _results;
          }
        });
      }
      return this;
    };

    Core.prototype.usePlugins = function() {
      var plugin, plugins, _i, _len;
      plugins = 1 <= arguments.length ? __slice.call(arguments, 0) : [];
      if ((plugins == null) || plugins.length === 0) {
        return this.log.warn('no plugins provided to use');
      }
      for (_i = 0, _len = plugins.length; _i < _len; _i++) {
        plugin = plugins[_i];
        this.use(plugin);
      }
      return this;
    };

    return Core;

  })();

  Facade = function(_, bootstrap) {
    var extend;
    extend = function(protoProps, staticProps) {
      var Surrogate, child, parent;
      parent = this;
      child = void 0;
      if (protoProps && _.has(protoProps, "constructor")) {
        child = protoProps.constructor;
      } else {
        child = function() {
          return parent.apply(this, arguments);
        };
      }
      _.extend(child, parent, staticProps);
      Surrogate = function() {
        this.constructor = child;
      };
      Surrogate.prototype = parent.prototype;
      child.prototype = new Surrogate;
      if (protoProps) {
        _.extend(child.prototype, protoProps);
      }
      child.__super__ = parent.prototype;
      return child;
    };
    Facade = function(webApplicationCore) {
      var _ref;
      if ((_ref = this.initialize) != null) {
        _ref.apply(this, arguments);
      }
      this.bus = {
        __listeners: {},
        __clear: function() {
          var channel, listener, _i, _len, _ref1;
          for (channel in this.__listeners) {
            _ref1 = this.__listeners[channel];
            for (_i = 0, _len = _ref1.length; _i < _len; _i++) {
              listener = _ref1[_i];
              this.off(channel, listener);
            }
          }
          return this.__listeners = {};
        },
        on: function(channel, callback, context) {
          webApplicationCore.bus.on(channel, callback, context);
          if (this.__listeners[channel] == null) {
            this.__listeners[channel] = [];
          }
          return this.__listeners[channel].push(callback);
        },
        off: function(channel, callback) {
          var index;
          webApplicationCore.bus.off(channel, callback);
          index = this.__listeners[channel].indexOf[callback];
          if (index > -1) {
            return this.__listeners[channel].splice(index, 1);
          }
        },
        emit: function(channel, data, callback) {
          return webApplicationCore.bus.emit(channel, data, callback);
        }
      };
      return this;
    };
    Facade.extend = extend;
    Facade._ = _;
    return Facade;
  };

  plugins = plugins || {};

  (plug = function(bus) {
    var console, logger, messageDataStore, messagesStore, method, methods, noop, previousDebug, previousError, previousLog, previousWarn, w, _i, _len;
    noop = function() {};
    methods = ['assert', 'clear', 'count', 'debug', 'dir', 'dirxml', 'error', 'exception', 'group', 'groupCollapsed', 'groupEnd', 'info', 'log', 'markTimeline', 'profile', 'profileEnd', 'table', 'time', 'timeEnd', 'timeStamp', 'trace', 'warn'];
    w = typeof window !== "undefined" && window !== null ? window : {};
    console = (w.console = w.console || {});
    for (_i = 0, _len = methods.length; _i < _len; _i++) {
      method = methods[_i];
      if (console[method] == null) {
        console[method] = noop;
      }
    }
    //previousError = console.error;
    //console.error = function() {
    //  var args, argument, _j, _len1;
    //  args = [];
    //  for (_j = 0, _len1 = arguments.length; _j < _len1; _j++) {
    //    argument = arguments[_j];
    //    args.push(argument);
    //    if (argument.stack != null) {
    //      args.push(argument.stack);
    //    }
    //  }
    //  previousError.apply(this, args);
    //  return messageDataStore.add('error', arguments);
    //};
    //previousLog = console.log;
    //console.log = function() {
    //  previousLog.apply(this, arguments);
    //  return messageDataStore.add('log', arguments);
    //};
    //previousWarn = console.warn;
    //console.warn = function() {
    //  previousWarn.apply(this, arguments);
    //  return messageDataStore.add('warn', arguments);
    //};
    //previousDebug = console.debug;
    //console.debug = function() {
    //  previousDebug.apply(this, arguments);
    //  return messageDataStore.add('debug', arguments);
    //};
    //console.dump = function() {
    //  return previousLog.apply(this, arguments);
    //};
    messagesStore = [];
    messageDataStore = {
      sizeLimit: 500,
      add: function(level, messages) {
        if (messagesStore.length > messageDataStore.sizeLimit) {
          messagesStore.splice(0, messageDataStore.sizeLimit * 0.1);
        }
        return messagesStore.push({
          level: level,
          time: new Date().getTime(),
          messages: messages
        });
      },
      list: function() {
        var message, _j, _len1, _results;
        _results = [];
        for (_j = 0, _len1 = messagesStore.length; _j < _len1; _j++) {
          message = messagesStore[_j];
          _results.push(console.dump(message.time, message.level, message.messages));
        }
        return _results;
      },
      getMessages: function() {
        return messagesStore;
      },
      clear: function() {
        return messagesStore.length = 0;
      }
    };
    logger = {
      id: 'logger',
      plugin: {
        logger: messageDataStore
      },
      Facade: {
        logger: {
          list: messageDataStore.list
        }
      }
    };
    return plugins.logger = function(bus) {
      return logger;
    };
  })();

  stem = function(_, bootstrap) {
    Facade(_);
    stem = {
      VERSION: "@@version",
      Bus: Bus,
      WebApp: Core,
      Facade: Facade,
      plugins: plugins || {},
      modules: {}
    };
    return stem;
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['underscore', 'cast.bootstrap'], function(_, bootstrap) {
      return stem(_, bootstrap);
    });
  } else if (typeof window !== "undefined" && window !== null) {
    window.stem = stem(window._, window.bootstrap);
  } else if ((typeof module !== "undefined" && module !== null ? module.exports : void 0) != null) {
    _ = require('./base/3rdParties/underscore/1.6.0/underscore');
    bootstrap = require('./base/assets/bootstrap/0.3.2/bootstrap.min');
    module.exports = stem(_, bootstrap);
  }

}).call(this);
