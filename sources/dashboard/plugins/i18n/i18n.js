(function() {
  var i18n;

  i18n = function(i18next, Handlebars, $) {
    var initialized = false;

    function validateInitialization(){
      // forbids the display of localized message as long as the i18n module has not been initialized
      if (!initialized){
        var error = new Error('i18n not initialized yet');
        alert('Internationalization component is being accessed but has not been initialized yet.\n'+error.stack );
        throw error;
      }
    }


    function translate(text, data){
      // validateInitialization(); // to enable once i18n init works
      // temp
      // var charRange = 254 - 128 - 1; // TODO remove when i18next is operational
      // return text
      // .split('')
      // .reduce(function(values, value){
      //   if (' ' === value){
      //     values.push(' ');
      //   }
      //   else {
      //     values.push(String.fromCharCode(128 + parseInt(Math.random()*charRange)));
      //   }
      //   return values;
      // }, [])
      // .join('');
      var options;
      if (data && data.hash){
        options = JSON.parse(JSON.stringify(data.hash));
      } else {
        options = {};
      }
      options.keySeparator = '.:.';
      result = i18next.t(text, options);
      return  result.length ? result:text;
    }

    Handlebars.registerHelper('t', translate);

    Handlebars.registerHelper('te', function(text, maxlength, shortText){
      textTranslation = translate(text);
      if (shortText && textTranslation.length > maxlength && typeof shortText == 'string'){
        return translate(shortText);
      }
      if (textTranslation.length > maxlength){
         return textTranslation.slice(0,maxlength-1) + '...';
      }
      return textTranslation;
    });

    return {
      id: 'i18n',
      Facade: {
        i18n: {
          init: function(options, callback) {

            $.when($.get('locales/en_US/translation.json'), $.get('locales/'+options.lng+'/translation.json')).done(function(dev, locale){
              options.resources = {dev:{translation:dev[0]}};
              // i18next does not support hyphen. So using underscore ('_') instead of hyphen ('-'). 
              options.lng = options.lng.replace('-', '_');
              options.resources[options.lng] = {translation:locale[0]};
              return i18next.init(options, callback);
            }).fail(function(error){
              console.error('could not load localization files', error);
              return i18next.init(options, callback);
            });


          },
          t: translate
        }
      }
    };
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) !== null) {
    define(['i18next', 'handlebars', 'jquery'], function(i18next, Handlebars, $) {
      return i18n(i18next,  Handlebars, $);
    });
  } else if ((typeof window !== "undefined" && window !== null) && (window.stem !== null)) {
    window.stem.plugins.i18n = i18n(i18next,  Handlebars, $);
  }

}).call(this);
