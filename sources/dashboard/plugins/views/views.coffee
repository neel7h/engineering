plugin = (_, $, $animo, Backbone, Handlebars, numeral, moment, Highcharts) ->

  findLastCSSRule = (ruleName) ->
    result = null
    for stylesheet in document.styleSheets
      for cssRule in stylesheet.cssRules
        result=cssRule if cssRule.selectorText?.indexOf(ruleName) > -1
    result

  findKeyframesRule = (ruleName) ->
    keyFrames = []
    for stylesheet in document.styleSheets
      for cssRule in stylesheet.cssRules
        if cssRule.name == ruleName
          keyFrames.push(cssRule) if [window.CSSRule.WEBKIT_KEYFRAMES_RULE, window.CSSRule.KEYFRAMES_RULE, window.CSSRule.MOZ_KEYFRAMES_RULE].indexOf(cssRule.type) > -1
    keyFrames

  includeCSSFile = (filePath) ->
    link = document.createElement( "link" );
    link.href = filePath;
    link.type = "text/css";
    link.rel = "stylesheet";
    link.media = "screen";
    document.getElementsByTagName( "head" )[0].appendChild( link );

  # remove old keyframes and add new ones
  change = (anim, x) ->
    keyframes = findKeyframesRule(anim)
    for keyFrame in keyframes
      keyFrame.deleteRule "0%"
      keyFrame.deleteRule "100%"
      newRule = "100% {-webkit-transform: translate3d(#{x}px, 0, 0); -moz-transform: translate3d(#{x}px, 0, 0); transform: translate3d(#{x}px, 0, 0);}"
      keyFrame.insertRule?(newRule) # Webkit, IE cssRule API
      keyFrame.appendRule?(newRule) # firefox cssRule API difference
    return

  # placeholder polyfill
  placeholder = ($selector) ->
    return if Modernizr.input.placeholder
    $selector.each(()->
      input = $(this)
      input.data('type',input.attr('type'))
      input.attr('type', 'text') if input.val() is "" and 'password' == input.attr('type')

      initial_value = input.attr("placeholder")
      input.val(initial_value)

      input.focus ->
        if input.val() is input.attr("placeholder")
          input.attr('type', input.data('type')) if 'password' == input.data('type')
          input.val("")
      input.blur ->
        if input.val() is ""
          input.attr('type', 'text') if  'password' == input.data('type')
          input.val(initial_value)
    )

  $.fn.spinner = (options)->
    settings = $.extend(true, $.fn.spinner.settings, options)
    this.each(()->
      $spinner = $('<div class="loading"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>')
      $spinner.addClass(settings.theme) if settings.theme?
      $spinner.appendTo(this)
    )

  $.fn.spinner.settings = {
    theme:null
  }

  Highcharts.setOptions({
    credits:
      enabled: false
      text: 'Highcharts.com'
      href: 'http://www.highcharts.com'
      position:
        align: 'right'
        x: -10
        verticalAlign: 'bottom'
        y: -5
      style:
        cursor: 'pointer'
        color: '#909090'
        fontSize: '9px'
    chart:
      zoomType: 'xy'
  })

  # Register common Handlebar helpers

  ### Number formatter ###
  Handlebars.registerHelper('formatNumber', (number, format) ->
    return '-' unless number?
    # return 'new' unless isFinite(number)
    return 'n/a' if isNaN(number)
    return numeral(number).format('0') unless format?
    return numeral(number).format(format)
  )

  Handlebars.registerHelper('isUndefined', (number, options) ->
    return options.fn(this)if number == undefined
    return options.inverse(this)
  )

  ### Number formatter ###
  Handlebars.registerHelper('formatBigNumber', (number) ->
    return '-' unless number?
    return 'N/A' if isNaN(number)
    if number < 1000
      return numeral(number).format('0,000')
    return numeral(number).format('0.0a')
  )

  Handlebars.registerHelper('assign', (context, code) ->
    componentStatus =context.violationDetails.component.status
    violationStatus=context.violationDetails.violation.status
    if code == "code"
      return componentStatus
    return violationStatus
  )

  ### Date formatter ###
  Handlebars.registerHelper('formatDate', (time, format) ->
    return moment.utc(time).format('MMM Do YYYY') unless format?
    return moment.utc(time).format(format)
  )

  Handlebars.registerHelper('issueType', (context) ->
   if $('.code-viewer .source-code-fragment-group').hasClass('critical')
     return "critical"
   else
     return "non-critical"
  )

  Handlebars.registerHelper('valueType', (context) ->
    paragraph = []
    if context.type == "integer"
      return context.values[0]
    else if context.type == "percentage"
      return (Math.round(context.values[0]*100)/100)+" %"
    else if context.type == "text"
      _.each(context.values, (values)-> paragraph += "<p>" + values + "</p>" )
      return paragraph
    else if context.type == "path"
      return paragraph
    else
      _.each(context.values, (values)-> paragraph += "<p>" + values.component.name + "</p>" )
      return paragraph
  )

  ### Ellipsis : text reduction after a number of characters. ###
  Handlebars.registerHelper('ellipsis', (text, maxlength, shortText) ->
    return shortText if shortText? and text.length > maxlength and typeof shortText == 'string'
    return text.slice(0,maxlength-1) + '...' if text.length > maxlength
    return text
  )

  ### Ellipsis : text reduction after a number of characters. ###
  Handlebars.registerHelper('ellipsisMiddle', (text, before = 10, after = 10) ->
    return text if (before + after) >= text.length
    return text.slice(0,before) + ' ... ' + text.slice(text.length-after, text.length)
  )

  Handlebars.registerHelper('ifDef', (conditional, options) ->
    if conditional == null
      return false
    return options.fn(this) if(conditional? and conditional != false)
    return options.inverse(this);
  )

  ### For visibilty of header in DialogView ###
  Handlebars.registerHelper('isHeaderVisible', (content, reset, options) ->
    return options.inverse(this) if(!content? and reset)
    return options.fn(this)

  )

  ### Checks equality of two values ###
  Handlebars.registerHelper('equals', (conditional, options) ->
    if (conditional == options.hash.value)
      return options.fn(this)
    else
      return options.inverse(this)
  )
  ### Checks if number is positive or not ###
  Handlebars.registerHelper('positive', (number, options) ->
    if( number > 0)
      return options.fn(this)
    return options.inverse(this)
  )


  DropDownDialogViews = DropDownDialogView($,_,Backbone, Handlebars,Highcharts, moment)

  views = (bus) ->
    ExpandableView = ExpandableViewPlugin(bus, _, Backbone, Handlebars)
    return {
      id: 'views'
      Facade:
        controllers:
          InvestigationController: controller(bus ,_ ,Backbone, ExpandableView, Handlebars)
        backbone:
          View:Backbone.View
          TileView:TileView(_, Backbone, Handlebars)
          ExpandableView:ExpandableView
          SectionContainerView:sections($, _, Backbone, Handlebars)
          GridContainerView:gridContainerView(_, Backbone, Handlebars)
          DialogView:DialogView($,_,Backbone.ModalView, Handlebars)
          DropDownDialogView:DropDownDialogViews.DropDownView
          ModalView:DropDownDialogViews.ModalView
          HelpDialogView:HelpDialogView($,_,Backbone.ModalView, Handlebars)
          MetricView:MetricView($, _, Backbone)
          ViolationDetailView: ViolationDetailView($, _, Backbone, Handlebars)
        Handlebars: Handlebars
        Charts:Highcharts
        tableHelpers:TableHelpers($,numeral, Handlebars)
        css:
          findLastCSSRule:findLastCSSRule
          includeCSSFile:includeCSSFile
        polyfill:
          placeholder:placeholder
        ui:
          spinner:($el, options)->
            return unless $el.spinner?
            return $el.spinner(options)
      }
  views

# AMD support (use in require)
if define?.amd?
  define([
      'underscore',
      'jquery',
      'animo',
      'backbone',
      'handlebars',
      'numberFormater',
      'moment',
      'highcharts',
      'jquery.gridster'
      'modaldialog'
    ],
    (_, $, $animo, Backbone, Handlebars, numeral, moment, Highcharts) ->
      return plugin(_, $, $animo, Backbone, Handlebars, numeral, moment, Highcharts)
  )
# direct browser integration (src include)
else if window?
  window.stem = window.stem or {}
  window.stem.plugins = window.stem.plugins or {}
  window.stem.plugins.views = plugin(_, $, $.animo, Backbone, Handlebars, numeral, moment, Highcharts)
else if module?.exports?
  module.exports = plugin(_, $, $.animo, Backbone, Handlebars, numeral, moment, Highcharts)
