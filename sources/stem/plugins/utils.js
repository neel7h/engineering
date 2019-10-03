(function() {
  var utils;

  utils = function(_, Nibbler, numeral, raphael, $) {
    var nibbler64, _utf8_decode, _utf8_encode;
    nibbler64 = new Nibbler({
      dataBits: 8,
      codeBits: 6,
      pad: '=',
      keyString: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    });
    _utf8_encode = function(string) {
      var c, n, utfText;
      string = string.replace(/\r\n/g, "\n");
      utfText = "";
      n = 0;
      while (n < string.length) {
        c = string.charCodeAt(n);
        if (c < 128) {
          utfText += String.fromCharCode(c);
        } else if ((c > 127) && (c < 2048)) {
          utfText += String.fromCharCode((c >> 6) | 192);
          utfText += String.fromCharCode((c & 63) | 128);
        } else {
          utfText += String.fromCharCode((c >> 12) | 224);
          utfText += String.fromCharCode(((c >> 6) & 63) | 128);
          utfText += String.fromCharCode((c & 63) | 128);
        }
        n++;
      }
      return utfText;
    };
    _utf8_decode = function(utfText) {
      var c, c2, c3, i, string;
      string = "";
      i = 0;
      c = 0;
      while (i < utfText.length) {
        c = utfText.charCodeAt(i);
        if (c < 128) {
          string += String.fromCharCode(c);
          i++;
        } else if ((c > 191) && (c < 224)) {
          c2 = utfText.charCodeAt(i + 1);
          string += String.fromCharCode(((c & 31) << 6) | (c2 & 63));
          i += 2;
        } else {
          c2 = utfText.charCodeAt(i + 1);
          c3 = utfText.charCodeAt(i + 2);
          string += String.fromCharCode(((c & 15) << 12) | ((c2 & 63) << 6) | (c3 & 63));
          i += 3;
        }
      }
      return string;
    };
    return {
      id: 'utils',
      Facade: {
        _: _,
        $: $,
        raphael: raphael,
        numeral: numeral,
        utils: {
          revertKeyValues: function(object) {
            return _.invert(object);
          }
        },
        base64: {
          encode: function(string) {
            if (string == null) {
              return null;
            }
            return nibbler64.encode(_utf8_encode(string));
          },
          decode: function(string) {
            if (string == null) {
              return null;
            }
            return _utf8_decode(nibbler64.decode(string));
          }
        }
      },
      plugin: {
        utils: {}
      }
    };
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['underscore', 'nibbler', 'numberFormater', 'raphael', 'jquery', 'jquery.splitter', 'jquery.noselect'], function(_, Nibbler, numeral, raphael, $) {
      return utils(_, Nibbler, numeral, raphael, $);
    });
  } else if ((typeof window !== "undefined" && window !== null) && (window.stem != null)) {
    window.stem.plugins['utils'] = utils(_, window.Nibbler, window.numeral, window.raphael, window.$);
  }

}).call(this);
