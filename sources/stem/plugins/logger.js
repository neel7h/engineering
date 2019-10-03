(function() {
  var plug, plugins;

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
    previousError = console.error;
    console.error = function() {
      var args, argument, _j, _len1;
      args = [];
      for (_j = 0, _len1 = arguments.length; _j < _len1; _j++) {
        argument = arguments[_j];

        if (argument instanceof Array){
          for(var k=0; k<argument.length; k++){
            args.push(argument[k]);
            if (argument[k].stack != null) {
              args.push(argument[k].stack);
            }
          }
        }
        else {
          args.push(argument);
          if (argument.stack != null) {
            args.push(argument.stack);
          }
        }

      }
      previousError.apply(this, args);
      return messageDataStore.add('error', arguments);
    };
    //previousLog = console.log;
    //console.logs = function() {
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
    console.dump = function() {
      return previousLog.apply(this, arguments);
    };
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

}).call(this);
