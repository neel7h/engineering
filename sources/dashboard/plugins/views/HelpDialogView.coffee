HelpDialogView = ($, _, ModalView, Handlebars)->


  Template =  '<div class="modal-header"><h2>{{title}}</h2><span id="close-button" class="close-button">&#xe62d;</span></div>
               <div class="modal-content">
               <div class="modal-left {{image}}"></div>
               <div class="modal-right">
                  <div class="modal-right-title"><h2>{{contentTitle}}</h2></div>
                  <div class="modal-right-content">{{{contentBody}}}</div>
                  <div class="modal-right-footer">{{{footerContent}}}</div>
               </div></div>'

  HelpDialog = ModalView.extend({
    id: 'help-modal-dialog'
    className: 'help-modal-dialog'
    template: Handlebars.compile(Template)
    defaultOptions:
      css:{} # override default values

    initialize:(options) ->
      @options = _.extend({
        title:'Select a title'
        image:''
        contentTitle:'Select a message'
        contentBody:''
        backgroundClickClosesModal:true
        onPerform:()->
          alert 'Define an action'
      }, options)
      ModalView.prototype.initialize.apply this, Array.prototype.slice.call(arguments, 0)
      @.on "closeModalWindow", ->
        $('#Container').removeClass('blur')

    events:
      'click #close-button' : 'cancel'

    cancel:() ->
      @hideModal()
      $('#container').removeClass('content-blur')

    render: ()->
      @$el.html(@template(@options))
      @showModal()
      $('#container').addClass('content-blur')
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
  HelpDialog