AdvanceSearchView = (facade) =>

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  AdvancedSearchSections = AdvancedSearchSections(facade)

  selectedRows = {'business-criteria':[],'technical-criteria':[],'quality-rules':[],'technology':[],'name':[],'weight':[],'critical':[],'status':[],'transactions':[]}

  sectionTemplate='<div class="detail-header"><p>{{View.prototype.title}}<span class="count"></span></p><div class="section-content"><div id="drill-{{id}}" class="drill-down"></div></div><footer></footer></div>'

  backbone.View.extend({
    localId:'sec_'
    sections:[]
    sectionTemplate:Handlebars.compile(sectionTemplate)
    template:Handlebars.compile('<div class="metric-page"
            <div class="content-header">
              <div class="selection-section"><p>{{t "Selection"}}</p><div class="selection"><button class="dot-drop-down"></button></div></div>
              <div id ="section" class="sections">
                <div class="sections-container">
                {{#each sections}}
                  <section id="{{sectionId}}">' + sectionTemplate + '</section>
                {{/each}}
                </div>
              </div>
            </div>
          </div>')

    events:
      'click .section-content':'_openSection'
      'click .dot-drop-down':'clearSelection'

    initialize:(options)->
      localStorage.setItem('resetSelector',true)
      @options = _.extend({}, options)
      @locaIds = []
      #remove local storage from navigating to other page
#      count = JSON.parse(localStorage.selectedCriteria).length if localStorage.selectedCriteria?
      @sections= [
        {
          id: 'business-criteria'
          View: AdvancedSearchSections.CriteriaOrRulesSection
#          count: count
        }
        {
          id: 'weight'
          View: AdvancedSearchSections.WeightSection
        }
        {
          id: 'critical'
          View: AdvancedSearchSections.CriticalSection
        }
        {
          id: 'status'
          View: AdvancedSearchSections.ViolationStatusSection
        }
        {
          id: 'transactions'
          View: AdvancedSearchSections.TransactionsSection
        }
        {
          id: 'technologies'
          View: AdvancedSearchSections.TechnologiesSection
        }
        {
          id: 'modules'
          View: AdvancedSearchSections.ModulesSection
        }
      ]
      for section in @sections
        section.sectionId = @localId + section.id
        @locaIds.push(section.sectionId)

    remove:()->
      for section in @sections
        section.view?.remove?()
      backbone.View.prototype.remove.apply(this, arguments)

    clearSelection:(event)->
      event.stopPropagation()
      @$el.find('.selection').append('<div class="option-drop-down"><div class="clear-section"><ul><li>' + t('Clear selection') + '</li></ul></div></div>') if !@$el.find('.clear-section').hasClass('disabled') and !$('.selection div').hasClass('clear-section')
      $clearSection = @$el.find('.option-drop-down')[0].style
      if $clearSection.display == "" or $clearSection.display == "none"
        $clearSection.display = "block"
      else $clearSection.display = "none"
      @$el.find('.clear-section').addClass('disabled').parent().attr('title',t('No filter selected')) and @$el.find('.option-drop-down').addClass('inactive') if @$el.find('.sections .detail-header p .count b').length == 0
      $('.clear-section').on 'click', =>
        facade.bus.emit('clearSearch',{
          filterSearch: selectedRows,
          pageId: 'advanceSearch',
        })
        @render()

    _openSection:(event)->
      $section = $(event.target)
      $section = $section.parents('section') unless $section.is('section')
      @openSection($section.attr('id'))

    showTable:(sectionId)->
      $section = @$el.find('#' + sectionId)
      id = $section.attr('id')
      $section.find('.section-content').children().addClass('open opening').removeClass('drill-down')
      $section.find('.detail-header').addClass('tableSection')
      $section.addClass('loadingSection')
      $section.find('footer').hide()

    openSection:(sectionId)->
      $section = @$el.find('#' + sectionId)
      id = $section.attr('id')
      if $section.find('.section-content').children().hasClass('drill-down') and !$section.find('.section-content').children().hasClass('opening')
        @showTable(sectionId)
        data = {}
        data[sectionId] = 1
        for section in @sections
          if section.sectionId == sectionId
            view = new section.View()
            section.view = view
            if view.model?
              view.model.getData({
                success:()->
                  $section.append(view.render($section))
              })
      else if $section.find('.section-content').children().hasClass('drill-down') and $section.find('.section-content').children().hasClass('opening')
        @showTable(sectionId)
        $section.find('#table-holder').show()
        $section.find('.search-box').show()
      else if $section.find('.section-content').children().hasClass('open')
        $section.find('.section-content').children().addClass('drill-down').removeClass('open')
        $section.find('#table-holder').hide()
        $section.find('.detail-header').removeClass('tableSection').css('height','35px')
        $section.removeClass('loadingSection')
        $section.find('footer').show()
        $section.find('.search-box').hide()

    render:()->
      $(document).click () =>
        $('.option-drop-down').hide() if $('.option-drop-down').css('display') == 'block'
      html = @$el.html(@template({sections:@sections}))
      html
    })
