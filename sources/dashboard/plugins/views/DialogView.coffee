DialogView = ($, _, ModalView, Handlebars)->

  Template = '<div class="modal-header {{image}}">
    <h2>{{title}}</h2>
    {{#if education}}<h3 {{#if multipleRules}} class = "more-rules" {{/if}} title="{{{subTitle}}}">{{ellipsis subTitle 50}}</h3>{{/if}}
    {{#if timeoutAlert}} <div class="display-timer"></div> {{/if}}
    </div>
    {{#isHeaderVisible content reset}}
      <div class="modal-body {{theme}}">
          <p>{{{message}}}</p>
      </div>
    {{/isHeaderVisible}}
    {{#if content}}
      <div class="modal-container">
          {{#unless reset}}
            <div class="modal-group">
              <textarea maxlength="250" required="required" id="comment">{{comment}}</textarea>
              <label class="control-label" for="textarea">{{commentPlaceholder}}</label><i class="bar {{theme}}"></i>
            </div>
          {{/unless}}
          {{#unless exclusion}}
            <select id="tag-list" class="select">
            </select>
            {{#if reset}}
              <div class="select-info"><p>{{t "The displayed list of languages are restricted to the availability"}} <br/>  {{t "of language locales in the application." }}</p></div>
              {{#unless isDefault}}
                <div class="modal-info"><p>{{t "The requested default language is unavailable for this application, Please contact" }} <br/> {{t "your administrator." }}</p></div>
              {{/unless}}
            {{/if}}
          {{/unless}}
          {{#if education}}
            <select id="action-list" class="select"></select>
          {{/if}}
      </div>
    {{/if}}
    <div class="modal-footer">
        <button id="perform" class="dialog-button dialog-button-{{theme}}">{{perform}}</button>
        {{#if timeoutAlert}}<button id="timeoutAlert" class="dialog-button dialog-button-{{theme}}">{{login}}</button>{{/if}}
        {{#if cancel}}<button id="cancel" class="dialog-button dialog-button-cancel">{{cancel}}</button>{{/if}}
    </div>
</div>'

  ConfirmDialog = ModalView.extend({
    id: 'confirm-modal-dialog'
    className: 'modal-dialog'
    template: Handlebars.compile(Template)
    defaultOptions:
      css:{} # override default values

    initialize:(options) ->
      plugin = require('plugins/i18n/i18n') #requireing i18n
      @t = plugin.Facade.i18n.t
      @options = _.extend({
        title:'Select a title'
        message:'Select a message'
        cancel:'Cancel'
        perform:'Ok'
        image: ''
        theme:''
        content: ''
        size: 'dialog-medium'
        backgroundClickClosesModal:options.cancel?
        onPerform:()->
          alert 'Define an action'
      }, options)
      delete @options.cancel if @options.timeoutAlert
      ModalView.prototype.initialize.apply this, Array.prototype.slice.call(arguments, 0)
      @.on "closeModalWindow", ->
        $('#Container').removeClass('blur')

    events:
      'click #cancel' : 'cancel'
      'click #timeoutAlert' : 'timeoutAlert'
      'click #perform' : 'perform'
      'keyup #comment' : 'buttonDisable'

    checkSessionTimeout:(duration, samlConfig)->
      if duration < 0
        message = 'application selection'
        message = 'welcome' if samlConfig
        $('#perform').addClass('btn-disable')
        $('#timeoutAlert').removeClass('btn-disable')
        $('.dialogMessage').html(@t('The Session has timed out. Please click on re&#45;login in order to login back again'))
        @$el.find('.modal-footer').append('<p class="session-info">' + @t('Note&#58; You will be redirected to '+message+' page on re&#45;login if single sign on is active.') + '</div>')
        @$el.find('.dialogMessage').addClass('textAlign') and $('.dialog-overlay').addClass('dialogBackground')
        duration = 0
        return
      $('.modal-header .display-timer').html('Time left:' + ' ' + duration)
      --duration
      $('#timeoutAlert').addClass('btn-disable') if duration > 0
      setTimeout(@checkSessionTimeout.bind(@, duration, samlConfig), 1000)

    timeoutAlert:()->
      @hideModal()
      $('#container').removeClass('content-blur')
      @options.onLogin()

    cancel:() ->
      @hideModal() if @options.cancel?
      $('#container').removeClass('content-blur')

    buttonDisable: (event) ->
      prioritySelected = $('.selected-priority .selected').text()
      actionsSelected = $('.selected-actions .selected').text()
      inputValue = event.currentTarget.value.trim()
      $('#select-holder .selected-actions').removeClass('show') and $('#select-holder .selected-priority').removeClass('show')
      if @options.comment == inputValue or $('.input-select').text() == @t("Select a Tag") and inputValue == "" or  @options.priority == undefined and @options.comment == undefined and prioritySelected == "" or @options.priority == ""  and @options.comment == "" and prioritySelected == "" and $('.input-select').length != 0
        if @options.comment == inputValue and @options.priority != undefined and @options.priority != prioritySelected.toLowerCase()
          $('#perform').removeClass('btn-disable')
        else if prioritySelected == "" or @options.actions?.label == actionsSelected or @options.priority == prioritySelected.toLowerCase() or @options.priority and @options.comment and @options.actions?.label
          $('#perform').addClass('btn-disable')
        else if actionsSelected != "" and prioritySelected == "" and inputValue == ""
          $('#perform').removeClass('btn-disable')
        else if @options.priority == undefined and @options.comment == undefined and prioritySelected != ""
          $('#perform').removeClass('btn-disable')
        else
          $('#perform').addClass('btn-disable')
      else if inputValue == ""
        $('#perform').addClass('btn-disable')
      else if @options.comment != inputValue and $('.selected-priority .input-select').text() == @options.tagList?.placeHolderEducation
        $('#perform').addClass('btn-disable')
      else
        $('#perform').removeClass('btn-disable')

      if $('.selected-priority').length == 0 and $('.selected-actions').length == 0 and @options.comment == undefined and inputValue != "" or $('.selected-priority').length = 0 and $('.selected-actions').length = 0 and @options.comment == ""
        $('#perform').removeClass('btn-disable')

    triggeredActions: ()->
      if @options.education
        options = ""
        actionList = [{"label": "Mark for action"}, {"label": "Mark for continuous improvement"}]
        actionList = @options.tagList.actions if @options.tagList.actions.length > 0
        actionList = @options.languageList if @options.languageList?.length > 0
        for i in [0..actionList?.length-1]
          option = actionList[i]
          if @options.actions?.label == actionList[i].label and option.label == actionList[i].label
            actionValue = option.label
            options += '<option selected= selected>' + option.label + '</option>'
          else
            options +=  "<option>" + option.label + "</option>"
        $("#action-list").html(options)
      tagList = [ {"label": "Low"}, {"label": "Moderate"}, {"label": "High"}, {"label": "Extreme"}]
      tagList = @options.tagList?.tag if @options.tagList?.tag?.length > 0
      tagList = @options.languageList if @options.languageList?.length > 0
      tagList.unshift({"label": ""}) if @options.tagList?.tag? and @options.tagList?.tag[0]?.label != ""
      options = ""
      for i in [0..tagList?.length-1]
        option = tagList[i]
        if @options.priority and @options.priority == option.label.toLowerCase()
          tagValue = option.label
          options += '<option selected= selected>' + option.label + '</option>'
        else
          if @options.action == 'reset'
            options += if option.value == localStorage.getItem("language") then "<option selected = selected value=#{option.value}>"+ option.label  + "</option>" else "<option value=#{option.value}>" + option.label + "</option>"
          else
            options +=  if i == 0 and option.label != "" then "<option selected = selected>" + option.label + "</option>" else "<option >" + option.label + "</option>"
      $("#tag-list").html(options)
      $.fn.initializeSelect = Window.initializeSelect
      placeholder = if @options.action == "reset" then @t("Select a Language") else if @t(@options.tagList?.placeHolderEducation) else @t(@options.tagList?.placeholder)
      if placeholder == "" or placeholder == undefined
        placeholder = if @options.action == "reset" then @t("Select a Language") else if @t("Select a Priority") else @t("Select a Tag for future violations")
      placeholder = if @options.education != undefined then @t(@options.tagList?.placeHolderEducation) else if @options.tagList? then @t(@options.tagList?.placeholder) else @t("Select a Language")
      if placeholder == "" or placeholder == undefined
        placeholder = if @options.tagList? @t("Select a Priority") else if @t("Select a Tag for future violations") else if @t("Select a Tag for future rules") else @t("Select a Language")
        @$el.find('.modal-dialog').addClass('education') if @options.education
      $('.modal-dialog .modal-header h2').addClass('educateHeader') if @options.education and $('.modal-dialog .modal-header h3').text() != ""
      $('select.select').initializeSelect(@options.theme, placeholder, tagValue, actionValue, @options.action)

    perform: (event) ->
      return if event.originalEvent.offsetX == 0 and event.originalEvent.offsetY == 0
      tag = @$el.find('select:first')[0]
      action = @$el.find('select:last')[0]
      if @options.action == 'reset'
        language = tag?.options[tag.selectedIndex].value.trim()
      else
        priority = tag?.options[tag.selectedIndex].label.toLowerCase().trim() if @options.priorityTag
        comment = @$el.find('#comment')[0]?.value
        if @options.education
          if action.options[action.selectedIndex].label.trim() == "Mark for action" then actions = true else actions = false
      @hideModal()
      $('#container').removeClass('content-blur')
      return @options.onPerform(language) if @options.action == 'reset'
      @options.onPerform(comment, priority, actions)

    render: ()->
      @options.size = 'dialog-small' if @options.action == "logout" || @options.action == "remove" || @options.action == "reset"
      @$el.addClass(@options.size)
      @options.content = null if @options.action == 'reset' and !@options.languageList
      @options.exclusion = true if !@options.priorityTag
      @options.exclusion = false if @options.action == "reset"
      @options.reset = true if @options.action == 'reset'
      that = @options
      @options.isDefault = !@options.defaultLanguage || _.find(@options.languageList, (language) -> return language.label.toLowerCase() == that.defaultLanguage?.toLowerCase()) if @options.action == 'reset'
      @$el.html(@template(@options))
      @showModal()
      $('#container').addClass('content-blur')
      @triggeredActions()
      selectorHolder = @$el.find('.select-holder')
      selectorHolder.first().addClass('selected-priority')
      selectorHolder.last().addClass('selected-actions') if !@options.language and @options.education
      @$el.find('.selected-actions').val(@options.actions?.label)
      @$el.find('.selected-priority').val(@options.priority)
      selectorHolder.attr('selected-language',@options.language) if @options.action == "reset"
      @$el.find('.modal-group textarea').val(@options.comment)
      if !@options.actions?.label or !@options.priority or @options.comment? or @options.comment == undefined
        $('#perform').addClass('btn-disable')
      $('#perform').focus()
      $('#perform').removeClass('btn-disable') if @options.button == true
      setTimeout(@checkSessionTimeout.bind(@, @options.duration, @options.samlConfig), 10) if @options.timeoutAlert
      return @

    ensureModalBlanket : () ->
      @modalBlanket = $("#modal-blanket");
      if @modalBlanket.length == 0
        @modalBlanket = $('<div class="dialog-overlay" id="modal-blanket">').appendTo(document.body).hide();
      return @modalBlanket

    click:(event)->
      if (event.target.id == "modal-blanket" && this.options.backgroundClickClosesModal)
        this.hideModal()
        $('#container').removeClass('content-blur')
  })
  ConfirmDialog