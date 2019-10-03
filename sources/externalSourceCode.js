Prism.hooks.add('complete', function (env) {
  if (!env.code) {
    return;
  }
  // works only for <code> wrapped inside <pre> (not inline)
  var pre = env.element.parentNode;
  var clsReg = /\s*\bline-numbers\b\s*/;
  if (
    !pre || !/pre/i.test(pre.nodeName) ||
      // Abort only if nor the <pre> nor the <code> have the class
    (!clsReg.test(pre.className) && !clsReg.test(env.element.className))
  ) {
    return;
  }

  var match = env.code.match(/\n(?!$)/g);
  var linesNum = match ? match.length + 1 : 1;
  if (999 < linesNum && linesNum < 10000 )
    pre.className = pre.className + ' more-than-thousands';
  if (9999 < linesNum && linesNum < 100000 )
    pre.className = pre.className + ' more-than-ten-thousands';
  if (99999 < linesNum && linesNum < 1000000 )
    pre.className = pre.className + ' more-than-hundred-thousands';
});

escape = (function () {
  tagsToReplace = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;'
  };
  return function (string) {
    return string.replace(/[&<>]/g, function (tag) {
      if (tagsToReplace[tag]){
        return tagsToReplace[tag];
      }
      else {
        return tag;
      }
    });
  };
})();

window.cast = {
  _utf8_encode : function (string) {
    string = string.replace(/\r\n/g,"\n");
    var utftext = "";
    for (var n = 0; n < string.length; n++) {
      var c = string.charCodeAt(n);
      if (c < 128) {
        utftext += String.fromCharCode(c);
      }
      else if((c > 127) && (c < 2048)) {
        utftext += String.fromCharCode((c >> 6) | 192);
        utftext += String.fromCharCode((c & 63) | 128);
      }
      else {
        utftext += String.fromCharCode((c >> 12) | 224);
        utftext += String.fromCharCode(((c >> 6) & 63) | 128);
        utftext += String.fromCharCode((c & 63) | 128);
      }
    }
    return utftext;
  },
  encodeBase64 : function (input) {
    var _keyStr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";
    var output = "";
    var chr1, chr2, chr3, enc1, enc2, enc3, enc4;
    var i = 0;
    input = cast._utf8_encode(input);
    while (i < input.length) {
      chr1 = input.charCodeAt(i++);
      chr2 = input.charCodeAt(i++);
      chr3 = input.charCodeAt(i++);
      enc1 = chr1 >> 2;
      enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
      enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
      enc4 = chr3 & 63;
      if (isNaN(chr2)) {
        enc3 = enc4 = 64;
      } else if (isNaN(chr3)) {
        enc4 = 64;
      }
      output = output +
      _keyStr.charAt(enc1) + _keyStr.charAt(enc2) +
      _keyStr.charAt(enc3) + _keyStr.charAt(enc4);
    }
    return output;
  },
  loginOnReturn:function(event){
    if (13 !== event.keyCode){
      return;
    }
    cast.login();
  },
  login:function(){
    var username = $('input#username').val();
    var password = $('input#password').val();
    var signature = cast.encodeBase64(username + ":" + password);
    $.ajax ({
      type:"GET",
      url: '../rest/login',
      dataType: "json",
      headers:{"Authorization":" Basic " + signature},
      success: function() {
        location.reload(true);
      },
      statusCode: {
        470: function() {
          console.error('error', $('.error-message'))

          $('.error-message').html("Invalid user name or password").show();
        }
      }
    });
  },
  placeholder:function($selector) {
    $selector.each(function() {
      var initial_value, input;
      input = $(this);
      input.data('type', input.attr('type'));
      if (input.val() === "" && 'password' === input.attr('type')) {
        input.attr('type', 'text');
      }
      initial_value = input.attr("placeholder");
      input.val(initial_value);
      input.focus(function() {
        if (input.val() === input.attr("placeholder")) {
          if ('password' === input.data('type')) {
            input.attr('type', input.data('type'));
          }
          return input.val("");
        }
      });
      return input.blur(function() {
        if (input.val() === "") {
          if ('password' === input.data('type')) {
            input.attr('type', 'text');
          }
          return input.val(initial_value);
        }
      });
    });
  },
  processSourceCode:function(domainId, componentId, snapshotId,$el, localSites, fileContents){
    var codeFragmentHref;
    if (localSites && fileContents){
      codeFragmentHref = domainId + '/local-sites/' + localSites + '/file-contents/' + fileContents;
    }
    $.ajax({
      type: 'GET',
      url: '../rest/' + domainId + '/components/' + componentId + '/snapshots/' + snapshotId + '/source-codes',
      headers: {
        accept: 'application/json'
      }
    }).done(function (data) {
      for (var i = 0; i < data.length; i++) {
          (function(codeFragment){
            if (codeFragmentHref && codeFragment.file.href !== codeFragmentHref) {
              return;
            }
            cast.processCodeFragment(codeFragment, codeFragment.file.href !== codeFragmentHref, $el);
            if (codeFragment) {
              $el.find('.code-fragment-name').html(codeFragment.file.name);
              $el.find('.code-fragment-name').prop('title', codeFragment.file.name);
            }
            else {
              $el.find('.code-fragment-name').html("File not found").addClass('error');
            }
            return;
          }
          (data[i]));
        }

      }).fail(function (error) {
        $el.find('.code-fragment-name').html("File not found").addClass('error');
      });
  },
  processCodeFragment:function(codeFragment, focusOnObject, $el) {
    var url = '../rest/' + codeFragment.file.href;
    if (focusOnObject){
      url += '?start-line='+codeFragment.startLine+'&end-line='+codeFragment.endLine;
    }
    $.ajax({
      type: 'GET',
      url: url,
      headers: {
        accept: 'text/plain'
      }
    }).done(function (data) {
      var fileName = codeFragment.file.name
      var extension = fileName.slice(fileName.lastIndexOf('.') + 1, fileName.length).toLowerCase();
      if (Prism.languages[extension] === undefined)
          extension = "java";
      if(window.location.href.indexOf('qualityRuleId') === -1) {
          var startLine = +window.location.href.split('startline=')[1].split('&')[0];
          var endLine = +window.location.href.split('endline=')[1].split('&')[0];
          var issueType = window.location.href.split('issueType=')[1].split('&')[0];
          var bookMark = window.location.href.split('highlightBookmark=')[1].split('&')[0];
          var secondaryBookmark = window.location.href.split('secondary=')[1];
          String.prototype.replaceAll = function (target, replacement) {
              return this.split(target).join(replacement);
          };
          var highlightedData = Prism.highlight(data, Prism.languages[extension])
          var tobeReplaced = highlightedData.split('\n').slice(startLine - 1, endLine).join('\n')
          var replaced = highlightedData.replaceAll(tobeReplaced, "<span class='source-bookmark'>" + tobeReplaced + "</span>")
          $el.find('code').html(replaced);

          scrollToBookmark = function (topLineNumber) {
            if(_.isUndefined($el.find($el.find('.line-numbers-rows span')[topLineNumber - 3]).position()))
              return;
              $el.find('.source-code').scrollTop($el.find($el.find('.line-numbers-rows span')[topLineNumber - 3]).position().top);
              // Using "-1" with topLineNumber to make sure scroll should be set with some display margin on top
          };

          var className;
          if (issueType === "non-critical") {
              className = 'bookmark-line';
              if (bookMark === "true")
                  $el.find('.source-bookmark').addClass('highlight-noncritical')
          } else {
              className = 'bookmark-object'
              if (bookMark === "true")
                  $el.find('.source-bookmark').addClass('highlight-critical')
          }

          if (secondaryBookmark === "true") {
              className = 'secondaryBookmark'
              $el.find('.source-bookmark').addClass('highlight-secondaryBookmark').removeClass('highlight-noncritical highlight-critical')
          }
          highlightLineNumber = function (startLineNumber, endLineNumber) {
              spansOfLineNumbers = $el.find('.line-number');
              $el.find(spansOfLineNumbers.slice(startLineNumber - 1, endLineNumber)).addClass(className);
          };
          Prism.highlightAll();
          highlightLineNumber(startLine, endLine)
          if (focusOnObject) {
              $el.find('pre.line-numbers').css('counter-reset', 'linenumber ' + (codeFragment.startLine - 1));
          }
          else {
              // highlightLineNumber(codeFragment.startLine,codeFragment.endLine);
              // scrollToBookmark(codeFragment.startLine);
              scrollToBookmark(startLine);
              if ($('.source-bookmark').length > 1) {
                _.each($($('.source-bookmark')), function (dom) {
                    if (!$(dom).visible()) {
                        $(dom).removeClass('highlight-noncritical highlight-critical highlight-secondaryBookmark')
                    }
                })
              }
          }
      } else {
          var highlightedData = Prism.highlight(data, Prism.languages[extension])
          $el.find('code').html(highlightedData);
          Prism.highlightAll();
      }
    }).fail(function (error) {
      $el.find('code').html('no code found').addClass('error');
    });
  },
  processMultipleFilesSourceCode:function(options){
    // parameters verification
    var codeFragmentHref, $el;
    $el = options.$el;

    $.ajax({
      type: 'GET',
      url: '../rest/' + options.domainId + '/components/' + options.componentId + '/snapshots/' + options.snapshotId + '/source-codes',
      headers: {
        accept: 'application/json'
      }
    }).done(function (data) {
      var selectorData = [];

      for(var i=0;i<data.length;i++){
        var item = data[i];
        item.id = _.uniqueId();
        selectorData.push({
          label: cast.ellipsisMiddle(item.file.name,22,40),
          value: item.id,
          selected: 0 === i
        });
      }
      var fileSelector = new bootstrap.Selector({name: 'select file', data: selectorData, class: 'light-grey', maxCharacters:66});
      fileSelector.on('selection', function(value){
        var item = _.findWhere(data,{id:value});
        cast.processCodeFragment(item, true, $el);
      });
      $el.find('.code-fragment-name').html(fileSelector.render());
      if (data.length === 1){
        fileSelector.disable();
      }
      cast.processCodeFragment(data[0], true, $el);
      }).fail(function (error) {
        $el.find('.code-fragment-name').html("File not found").addClass('error');
      });
  },
  processObjectSelector:function(domainId,snapshotId, qualityRuleId, master, selectedComponentId, $el){
     $.ajax({
      type: 'GET',
      url: '../rest/' + domainId + '/components/' + master + '/snapshots/' + snapshotId + '/findings/'+qualityRuleId,
      headers: {
        accept: 'application/json'
      }
    }).done(function(data){
      if (data === undefined || data.values.length===0 ) return [];
      var objects = data.values[0];
      var list = [];
      for(var i=0; i<objects.length;i++){
        var item = objects[i];
        list.push({
          label: '<span title="' + item.component.name +  '">' + escape(cast.ellipsisMiddle(item.component.name,10,30)) + '</span>',
          value: item.component.href,
          selected: item.component.href.split('/')[2] === selectedComponentId.toString()
        });
      }
      var componentSelector = new bootstrap.Selector({name: 'select component', data: list, class: 'light-grey', maxCharacters:66666});
      componentSelector.on('selection', function(item){
        var currentComponent = item.split('/')[2];
        cast.processMultipleFilesSourceCode({domainId:domainId, componentId:currentComponent, snapshotId:snapshotId, $el:$el});
      });
      $el.find('.component-selector').html(componentSelector.render());
    });
  },
  ellipsisMiddle:function(text, before, after){
    if (before === null) {
      before = 10;
    }
    if (after === null) {
      after = 10;
    }
    if((before + after) >= text.length){
      return text;
    }
    else{
      return text.slice(0,before) + ' ... ' + text.slice(text.length-after, text.length);
    }

  }
};
