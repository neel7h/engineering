(function() {
  var Menu, Selector, Table, TreeExplorer, bootstrap, closableItems, ellipsis;

  Menu = function($, _, Backbone, Handlebars, ipadHelper) {

    /*
      Menu
      inputs:
        text: menu label
        class: specific css class to use a customized form of the menu
        items: data array containing
          text: menu item label
          class: css class to add e.g. an icon
          href: an associated hyperlink
          action: a function to be called on menu click if no href was defined
          separator: boolean to present a menu separation after the item
      outputs:
        a single menu div container
      triggers:
        'menu-selection': event triggered if an item is selected; the item is provided as the event parameter.
     */
    return Backbone.View.extend({
      tagName: 'div',
      className: 'drop-down',
      template: Handlebars.compile('<div class="selector"> <span class="label">{{{text}}}</span> <a onfocus="this.blur();"></a> </div> <div class="cont"> <ul class="options"> {{#each items}} <li class="selectable {{#if separator}}separator{{else}}no-separator{{/if}}" data-ref="{{reference}}" data-href="{{href}}" {{#if title}}title="{{title}}"{{/if}}><div class="label {{class}}">{{{text}}}</div></li> {{/each}} </ul></div>'),
      events: (function() {
        if (ipadHelper.isIpad()) {
          return {
            'touchend .selector': '_toggleMenu',
            'touchend .options .selectable': 'selectItem',
            'touchmove .options .selectable': 'scroll',
            'touchstart .options .selectable': 'prepareItemSelection'
          };
        } else {
          return {
            'click .selector': '_toggleMenu',
            'click .options .selectable': 'selectItem'
          };
        }
      })(),
      initialize: function(options) {
        var $window, index, j, len, ref, sample;
        this.options = this.options || options;
        closableItems.addItem(this);
        index = 0;
        ref = this.options.items;
        for (j = 0, len = ref.length; j < len; j++) {
          sample = ref[j];
          sample.reference = index++;
        }
        $window = $(window);
        $window.on('resize', _.debounce((function(_this) {
          return function() {
            return _this._resize();
          };
        })(this), 100));
        if (false) {
          return $window.on('touchend', this, this._toggleMenuThenPropagate);
        } else {
          return $window.on('click', this, this._toggleMenuThenPropagate);
        }
      },

      /*Tear down */
      remove: function() {
        $(window).off('resize', this._resize).off('click touchend', this._toggleMenuThenPropagate);
        return closableItems.removeItem(this);
      },

      /*
        /!\ time consuming, do not hesitate to _.debounce in order to reducing browser workload
       */
      _resize: function() {
        var base, containerWidth, contentMaxHeight, height, selector, selectorWidth, tooMuch;
        if (this.$cont == null) {
          this.$cont = this.$el.find('.cont');
        }
        if (this.$el.hasClass('opened')) {
          this.$el.find('.tooltiptext').hide();
        } else {
          this.$el.find('.tooltiptext').show();
        }
        if (this.options.alignRight) {
          selector = this.$el.find('.selector');
          containerWidth = this.$cont.outerWidth();
          selectorWidth = selector.outerWidth();
        }
        if (!this.$el.hasClass('opened')) {
          return;
        }
        tooMuch = ($(window).height() - (this.$cont.offset().top - $(document).scrollTop()) - this.$cont.height()) - 20;
        contentMaxHeight = this.$cont.find('.options').height();
        if (tooMuch < 0) {
          height = this.$cont.height() + tooMuch;
          this.$cont.height(height);
        } else {
          if (this.$cont.height() < this.$cont.css('max-height').replace('px', '')) {
            height = Math.min(contentMaxHeight, this.$cont.height() + tooMuch);
            this.$cont.height(height);
          }
        }
        return typeof (base = this.$el.find('.cont')).scroller === "function" ? base.scroller('computeSize', {
          height: height || this.$cont.height(),
          scrollableAreaHeight: contentMaxHeight
        }) : void 0;
      },
      onShow: function() {
        return this._resize();
      },
      render: function() {
        var container, html;
        this.$cont = void 0;
        if (this.options["class"] != null) {
          this.$el.addClass(this.options["class"]);
        }
        html = this.$el.html(this.template(this.options));
        container = this.$el.find('.cont');
        if (typeof container.scrollerInit === "function") {
          container.scrollerInit({
            scrollId: "detail" + this.options.name,
            horizontalPane: false,
            scrollableArea: this.$el.find('.options')
          });
        }
        return html;
      },
      _toggleMenu: function(event) {
        event.stopPropagation();
        event.preventDefault();
        if (this.$el.hasClass('opened')) {
          return this.close();
        } else {
          return this.open();
        }
      },
      _toggleMenuThenPropagate: (function(_this) {
        return function(event) {
          var ref, ref1;
          if (((ref = event.data) != null ? ref.close : void 0) != null) {
            return (ref1 = event.data) != null ? ref1.close() : void 0;
          }
        };
      })(this),

      /* Open a selector (closes all registered selectors on the same time) */
      open: function() {
        this.$el.find('.tooltiptext').hide();
        closableItems.close();
        this.$el.addClass('opened');
        return _.delay((function(_this) {
          return function() {
            return _this._resize();
          };
        })(this), 50);
      },

      /* Closes the selection menu */
      close: function() {
        this.$el.find('.tooltiptext').show();
        return this.$el.removeClass('opened');
      },
      prepareItemSelection: function() {
        this.scrolling = false;
        return true;
      },
      scroll: function() {
        this.scrolling = true;
        return true;
      },
      selectItem: function(event) {
        var menuItem, target;
        event.stopPropagation();
        event.preventDefault();
        target = $(event.target);
        if (target.hasClass('label')) {
          target = target.parent('LI');
        }
        if ('SPAN' === target.prop('tagName')) {
          target = target.parents('LI');
        }
        if (!target.hasClass('selectable')) {
          return;
        }
        if (!this.$el.hasClass('opened')) {
          return;
        }
        if (this.scrolling) {
          return;
        }
        menuItem = this.options.items[target.attr('data-ref')];
        if (menuItem.href != null) {
          this.close();
          if (menuItem.target) {
            return window.open(menuItem.href, menuItem.target);
          } else {
            return window.location = menuItem.href;
          }
        } else {
          if (menuItem.action != null) {
            menuItem.action(menuItem);
          }
          this.trigger('menu-selection', menuItem);
          return this.close();
        }
      },
      getSelectedItem: function() {
        return this.selectedData;
      }
    });
  };

  Selector = function($, _, Backbone, Handlebars, ipadHelper) {

    /*
      Selector
      inputs:
      maxCharacters: set the value to truncate the selected item. Null by default.
      name: html input name attribute (links to input id)
      class: specific css class to use a customized form of the menu
      data: data array containing:
        label: the option message displayed.
        value:  the option value to be set in the input field.
                if no value is provided, field is skipped from the listing.
                if first data sample has no value, it is considered as a 'Select value' non selectable label.
        selected: optional, undefined by default. Defines the data sample selected by default.
                  If more than one data sample is selected, the first sample is considered.
                  If no data sample are selected, the first sample is selected.
      outputs:
        input with the given name exists where you put it (can be consumed as a form input)
      triggers:
        'selection':value return the selected data value on selection change
     */
    return Backbone.View.extend({
      tagName: 'div',
      className: 'drop-down',
      template: Handlebars.compile('<div class="selector"> <span class="label">{{{selectedDataLabel}}}</span> <a onfocus="this.blur();"></a> <input type="hidden" name="{{options.name}}" {{#if selectedDataValue}}value="{{selectedDataValue}}"{{/if}}> </div> <div class="cont"> <ul class="options"> {{#each options.data}} {{#if hasValue}} <li class="selectable {{#if selected}}selected{{/if}}" data-ref="{{reference}}" data-value="{{value}}"><div class="label">{{{label}}}</div></li> {{/if}} {{/each}} </ul></div>'),
      events: (function() {
        if (ipadHelper.isIpad()) {
          return {
            'touchend .selector': '_toggleMenu',
            'touchend .options .selectable': 'selectItem',
            'touchmove .options .selectable': 'scroll',
            'touchstart .options .selectable': 'prepareItemSelection'
          };
        } else {
          return {
            'click .selector': '_toggleMenu',
            'click .options .selectable': 'selectItem'
          };
        }
      })(),
      initialize: function(options) {
        var $window, index, j, len, ref, sample;
        this.options = this.options || options;
        closableItems.addItem(this);
        index = 0;
        ref = this.options.data;
        for (j = 0, len = ref.length; j < len; j++) {
          sample = ref[j];
          sample.reference = index++;
          sample.hasValue = sample.value != null;
          if (sample.selected) {
            if (this.selectedData != null) {
              sample.selected = false;
            } else {
              this.selectedData = sample;
            }
          }
        }
        if (this.selectedData == null) {
          this.selectedData = this.options.data[0];
        }
        $window = $(window);
        $window.on('resize', _.debounce((function(_this) {
          return function() {
            return _this._resize();
          };
        })(this), 100));
        if (ipadHelper.isIpad()) {
          return $window.on('touchend', this, this._toggleMenuThenPropagate);
        } else {
          return $window.on('click', this, this._toggleMenuThenPropagate);
        }
      },

      /*Tear down */
      remove: function() {
        $(window).off('resize', this._resize).off('click touchend', this._toggleMenuThenPropagate);
        return closableItems.removeItem(this);
      },
      enableOptions: function(optionValues, title) {
        return this.$el.find('.cont li').removeAttr("title").removeClass('inactive').each(function(i, element) {
          var $e, value;
          $e = $(element);
          value = $e.attr('data-value');
          if (optionValues == null) {
            return $e;
          }
          if (optionValues.length === 0) {
            return $e;
          }
          if (optionValues.indexOf(value) === -1) {
            $e.attr('title', title);
            return $e.addClass('inactive');
          }
        });
      },
      enable: function() {
        return this.$el.removeClass('disabled');
      },
      disable: function() {
        this.close();
        return this.$el.addClass('disabled');
      },

      /*
        /!\ time consuming, do not hesitate to _.debounce in order to reducing browser workload
       */
      _resize: function() {
        var base, contentMaxHeight, height, tooMuch;
        if (!this.$el.hasClass('opened')) {
          return;
        }
        if (this.$cont == null) {
          this.$cont = this.$el.find('.cont');
        }
        tooMuch = ($(window).height() - (this.$cont.offset().top - $(document).scrollTop()) - this.$cont.height()) - 20;
        contentMaxHeight = this.$cont.find('.options').height();
        if (tooMuch < 0) {
          height = this.$cont.height() + tooMuch;
          this.$cont.height(height);
        } else {
          if (this.$cont.height() < this.$cont.css('max-height').replace('px', '')) {
            height = Math.min(contentMaxHeight, this.$cont.height() + tooMuch);
            this.$cont.height(height);
          }
        }
        if (typeof (base = this.$el.find('.cont')).scroller === "function") {
          base.scroller('computeSize', {
            height: height || this.$cont.height(),
            scrollableAreaHeight: contentMaxHeight
          });
        }
        if (height <= contentMaxHeight) {
          return this.$el.find('.options').addClass('no-scroll');
        } else {
          return this.$el.find('.options').removeClass('no-scroll');
        }
      },
      render: function() {
        var container, html;
        this.$cont = void 0;
        if (this.options["class"] != null) {
          this.$el.addClass(this.options["class"]);
        }
        html = this.$el.html(this.template({
          options: this.options,
          selectedDataLabel: this.selectedData.label,
          selectedDataValue: this.selectedData.value
        }));
        if (this.options.data.length === 1) {
          html.find('.selector').addClass('disable-selector');
          html.find('.selector a').addClass('custom-hidden');
        }
        if (this.selectedData.label.length > this.options.maxCharacters) {
          html.find('.selector .label').html(ellipsis(this.selectedData.label, this.options.maxCharacters)).attr('title', this.selectedData.label);
        }
        container = this.$el.find('.cont');
        if (typeof container.scrollerInit === "function") {
          container.scrollerInit({
            scrollId: "detail" + this.options.name,
            horizontalPane: false,
            scrollableArea: this.$el.find('.options')
          });
        }
        if (container.scrollerInit == null) {
          container.css('overflow-y', 'auto');
        }
        return html;
      },
      _toggleMenu: function(event) {
        event.stopPropagation();
        event.preventDefault();
        if (this.$el.hasClass('disabled')) {
          return;
        }
        if (this.$el.hasClass('opened')) {
          return this.close();
        } else {
          return this.open();
        }
      },
      _toggleMenuThenPropagate: (function(_this) {
        return function(event) {
          var ref, ref1;
          if (((ref = event.data) != null ? ref.close : void 0) != null) {
            return (ref1 = event.data) != null ? ref1.close() : void 0;
          }
        };
      })(this),

      /* Open a selector (closes all registered selectors on the same time) */
      open: function() {
        closableItems.close(this);
        this.$el.addClass('opened');
        return _.delay((function(_this) {
          return function() {
            return _this._resize();
          };
        })(this), 50);
      },

      /* Closes the selection menu */
      close: function() {
        return this.$el.removeClass('opened');
      },
      selectValue: function(value) {
        var target;
        target = this.$el.find('.options li[data-value="' + value + '"]');
        return this._performItemSelection(target, value);
      },
      _performItemSelection: function(target, value) {
        var newLabel, selector;
        this.$el.find('.selectable').removeClass('selected');
        target.addClass('selected');
        this.selectedData = this.options.data[target.attr('data-ref')];
        selector = this.$el.find('.selector');
        selector.find('input').attr('value', value);
        newLabel = target.find('.label').html();
        if (newLabel) {
          if (newLabel.length > this.options.maxCharacters) {
            selector.find('.label').html(ellipsis(newLabel, this.options.maxCharacters)).attr('title', newLabel);
          } else {
            selector.find('.label').html(newLabel);
          }
        }
        this.trigger('selection', value);
        return this.close();
      },
      prepareItemSelection: function() {
        this.scrolling = false;
        return true;
      },
      scroll: function() {
        this.scrolling = true;
        return true;
      },
      selectItem: function(event) {
        var target, value;
        event.stopPropagation();
        event.preventDefault();
        target = $(event.target);
        if (target.nodeName !== 'LI') {
          target = target.closest('LI');
        }
        if (target.hasClass('inactive')) {
          return;
        }
        if (!target.hasClass('selectable')) {
          return;
        }
        if (!this.$el.hasClass('opened')) {
          return;
        }
        if (this.scrolling) {
          return;
        }
        value = target.attr('data-value');
        return this._performItemSelection(target, value);
      },
      getSelectedItem: function() {
        return this.selectedData;
      }
    });
  };

  Table = function($, _, Backbone, Handlebars, numeral) {

    /*
       Table
       inputs:
         [ ] footer: table footer
         [ ] headers
           [ ] sorter: 'none', 'string', 'date', 'numeric', function
         [ ] rows
       outputs:
         A table html object
       triggers:
         'sorted' : event triggered on column sort, provides the selected column
       listenTo:
         'group' : null to ungroup, column number to group by column
     */
    return Backbone.View.extend({
      tagName: 'div',
      className: 'table',
      template: Handlebars.compile('<table class="table"><thead> <tr> {{#if rowSelector}} <th class="center row-selector" title="Select all currently displayed"> <input type="checkbox" id="toggle-header" /> <label for="toggle-header"></label> </th> {{/if}} {{#each columns}} <th class="{{setAlignment @index}}{{setLength @index}}" {{#if title}}title="{{title}}"{{/if}}> {{#if headerMin}}<span class="min{{#if order}} {{order}}{{/if}} {{#if selector}}selector{{#if selector.active}} active{{/if}}{{else}}sort{{/if}}" data-label="{{{processSpecialCharacters headerMin}}}" data-column="{{@index}}">{{{processSpecialCharacters headerMin}}}</span>{{/if}} <span class="{{#if order}}{{order}} {{/if}}{{#if headerMin}}max{{/if}} {{#if selector}}selector{{#if selector.active}} active{{/if}}{{else}}sort{{/if}}" data-label="{{#if labelIcon}}<label>{{processSpecialCharacters labelIcon}} </label>{{/if}}{{{header}}}" data-column="{{@index}}">{{#if labelIcon}}<label>&{{labelIcon}} </label>{{/if}}{{{header}}}</span> </th> {{/each}} </tr> </thead><thead class="invisible-sticky-scroll"> <tr> {{#if rowSelector}} <th class="center row-selector" title="Select all currently displayed"> <input type="checkbox" id="toggle-header" /> <label for="toggle-header"></label> </th> {{/if}} {{#each columns}} <th class="{{setAlignment @index}}{{setLength @index}}" {{#if title}}title="{{title}}"{{/if}}> {{#if headerMin}}<span class="min{{#if order}} {{order}}{{/if}} {{#if selector}}selector{{#if selector.active}} active{{/if}}{{else}}sort{{/if}}" data-label="{{{processSpecialCharacters headerMin}}}" data-column="{{@index}}">{{{processSpecialCharacters headerMin}}}</span>{{/if}} <span class="{{#if order}}{{order}} {{/if}}{{#if headerMin}}max{{/if}} {{#if selector}}selector{{#if selector.active}} active{{/if}}{{else}}sort{{/if}}" data-label="{{#if labelIcon}}<label>{{processSpecialCharacters labelIcon}} </label>{{/if}}{{{header}}}" data-column="{{@index}}">{{#if labelIcon}}<label>&{{labelIcon}} </label>{{/if}}{{{header}}}</span> </th> {{/each}} </tr> </thead><tbody> {{#if groups}} {{#each groups}} {{setGroupKey @key}} <tr> <td colspan="1" class="group {{#if closed}}closed{{else}}opened{{/if}}" group-index="{{@key}}">{{@key}}</td> {{#each aggregates}} {{#showAggregate @index}} <td class="aggregate {{setAlignment @index}}">{{{aggregateColumn @index this}}}</td> {{else}} <td class="aggregate"></td> {{/showAggregate}} {{/each}} </tr> {{#each rows}} {{setRowIndex @index}} <tr class="in-group {{#if ../closed}}closed{{else}}opened{{/if}} {{#if ../click}}clickable  {{setSelected this}}{{/if}}" group-index="{{@../key}}" data-index="{{@index}}" {{#if id}}data-id="{{id}}"{{/if}}> {{#each columns}} <td class="{{setAlignment @index}}" {{#if id}}data-id="{{id}}"{{/if}}> <span>{{{formatRow this @index}}}</span></td> {{/each}} </tr> {{/each}} {{/each}} {{else}} {{#each rows}} {{setRowIndex @index}} <tr {{#if id}}data-id="{{id}}"{{/if}} data-index="{{@index}}" class="{{#if className}}{{className}}{{/if}}{{#if ../click}} clickable {{setSelected this}}{{/if}}" {{#each data}} data-{{label}}="{{value}}" {{/each}} > {{#if ../rowSelector}} <td class="center row-selector"> <input type="checkbox" id="toggle-{{@index}}" {{#if rowSelected}}checked{{/if}}/> <label for="toggle-{{@index}}"></label> </td> {{/if}} {{#each columns}} <td class="{{setAlignment @index}}" {{#if id}}data-id="{{id}}"{{/if}}>{{{formatRow this @index }}}</td> {{/each}} </tr> {{/each}} {{/if}} </tbody></table>'),
      events: {
        'click th span.sort': 'sortColumn',
        'click tr th.row-selector label': 'toggleAllRowInputSelectors',
        'click tr td.row-selector label': 'toggleRowInputSelector',
        'click tr.clickable td:not(.row-selector)': 'actionOnRow',
        'click td.group': 'openOrCloseGroup'
      },
      initialize: function(options) {
        var column, j, k, len, len1, ref, ref1, results, row;
        this.options = _.extend({}, this.options, options);
        ref = this.options.rows.models;
        for (j = 0, len = ref.length; j < len; j++) {
          row = ref[j];
          row.set('_bootstrapTableId', row.cid);
        }
        this.selectedGroupBy = options.groupBy;
        ref1 = this.options.columns;
        results = [];
        for (k = 0, len1 = ref1.length; k < len1; k++) {
          column = ref1[k];
          results.push(column.aggregate != null ? column.aggregate : column.aggregate = 'sum');
        }
        return results;
      },
      toggleAllRowInputSelectors: function(event) {
        var $target, checked, j, len, model, ref;
        if (this.options.rows.length === 0) {
          this.trigger('update:row-selector', {
            hasChecked: false
          });
          return false;
        }
        $target = $(event.target).siblings('input');
        checked = $target.is(':checked');
        if (checked) {
          this.$el.find('.row-selector input[type="checkbox"]').prop('checked', false);
        } else {
          this.$el.find('.row-selector input[type="checkbox"]').prop('checked', true);
        }
        this.$el.find('.row-selector.hide-row input[type="checkbox"]').prop('checked', false);
        ref = this.options.rows.models;
        for (j = 0, len = ref.length; j < len; j++) {
          model = ref[j];
          model.set('rowSelected', !checked);
        }
        _.each(this.$el.find('.hide-row'), (function(dom) {
          this.options.rows.findWhere({
            id: dom.parentElement.dataset.id
          }).set('rowSelected', false);
        }), this);
        this.trigger('update:row-selector', {
          hasChecked: !checked
        });
        return false;
      },
      toggleRowInputSelector: function(event) {
        var $headerInput, $i, $inputEle, checkedBeforeClick, hasChecked, index, j, len, model, ref, row;
        $inputEle = $(event.target).siblings('input');
        $headerInput = this.$el.find('th.row-selector input[type="checkbox"]');
        if ($headerInput.is(':checked') && $inputEle.is(':checked')) {
          $headerInput.prop('checked', false);
        }
        $i = $($inputEle.parents('tr')[0]);
        index = $i.attr('data-index');
        model = this.options.rows.at(index);
        checkedBeforeClick = (model != null ? model.get('rowSelected') : void 0) || false;
        model.set('rowSelected', !checkedBeforeClick);
        if (model && !checkedBeforeClick) {
          row = model;
        }
        $inputEle.prop('checked', !checkedBeforeClick);
        hasChecked = false;
        ref = this.options.rows.models;
        for (j = 0, len = ref.length; j < len; j++) {
          model = ref[j];
          if (model.get('rowSelected')) {
            hasChecked = true;
            break;
          }
        }
        this.trigger('update:row-selector', {
          hasChecked: hasChecked,
          row: row,
          isShift: event.shiftKey
        });
        return false;
      },
      getSelectedRows: function() {
        return this.options.rows.where({
          rowSelected: true
        });
      },
      remove: function() {

        /*
          groupBy:(key) groups the table by the groups:key;
          'none', -1, null or undefined are considered to remove group.
         */
      },
      groupBy: function(groupKey) {
        if (groupKey === this.selectedGroupBy) {
          return;
        }
        if (['none', -1, null, void 0].indexOf(groupKey) > -1) {
          this.selectedGroupBy = null;
        } else {
          this.selectedGroupBy = groupKey;
        }
        return this.render();
      },
      render: function(options) {
        var $colspan, column, columnIndex, data, direction, fn, group, groups, html, i, index, items, j, k, l, len, len1, len2, len3, len4, m, n, o, oldGroups, p, q, r, ref, ref1, ref10, ref2, ref3, ref4, ref5, ref6, ref7, ref8, ref9, row, rowGroups, s, that;
        if (this.selectedGroupBy != null) {
          if (this.groups != null) {
            oldGroups = this.groups;
          }
          this.groups = {
            'no group': {
              rows: [],
              aggregate: 0,
              aggregates: []
            }
          };
          ref = this.options.rows.toJSON();
          for (j = 0, len = ref.length; j < len; j++) {
            row = ref[j];
            rowGroups = (ref1 = row.groups) != null ? ref1[this.selectedGroupBy] : void 0;
            if ((rowGroups == null) || rowGroups.length === 0) {
              this.groups['no group'].rows.push(row);
              for (index = k = 0, ref2 = this.options.columns.length - 1; 0 <= ref2 ? k <= ref2 : k >= ref2; index = 0 <= ref2 ? ++k : --k) {
                if (this.groups['no group'].aggregates[index] == null) {
                  this.groups['no group'].aggregates[index] = 0;
                }
                if (isNaN(row.columns[index])) {
                  continue;
                }
                this.groups['no group'].aggregates[index] += row.columns[index];
              }
              this.groups['no group'].aggregate += row.columns[row.columns.length - 1];
              continue;
            }
            for (l = 0, len1 = rowGroups.length; l < len1; l++) {
              group = rowGroups[l];
              if (this.groups[group] == null) {
                this.groups[group] = {
                  rows: [],
                  aggregate: 0,
                  aggregates: []
                };
              }
              this.groups[group].rows.push(row);
              for (index = m = 0, ref3 = this.options.columns.length - 1; 0 <= ref3 ? m <= ref3 : m >= ref3; index = 0 <= ref3 ? ++m : --m) {
                if (this.groups[group].aggregates[index] == null) {
                  this.groups[group].aggregates[index] = 0;
                }
                if (isNaN(row.columns[index])) {
                  if (row.columns[index] !== "N/A") {
                    continue;
                  }
                }
                if (((ref4 = row.groups.appMarqCriterion) != null ? ref4.appMarqcolumnNumber : void 0) === index && row.groups.appMarqCriterion) {
                  if (row.groups.appMarqCriterion.filter) {
                    this.groups[group].aggregates[index] = "N/A";
                  } else {
                    this.groups[group].aggregates[index] = Number(row.groups.appMarqCriterion.average);
                  }
                } else {
                  this.groups[group].aggregates[index] += row.columns[index];
                }
              }
              this.groups[group].aggregate += row.columns[row.columns.length - 1];
            }
          }
          for (group in this.groups) {
            if (this.groups[group].rows.length === 0) {
              delete this.groups[group];
              continue;
            }
            row = this.groups[group].rows[0];
            for (index = n = 0, ref5 = this.options.columns.length - 1; 0 <= ref5 ? n <= ref5 : n >= ref5; index = 0 <= ref5 ? ++n : --n) {
              if (isNaN(row.columns[index])) {
                if (((ref6 = row.groups.appMarqCriterion) != null ? ref6.gapColumnNumber : void 0) !== index) {
                  continue;
                }
              }
              if (this.options.columns[index].aggregate === 'average') {
                this.groups[group].aggregates[index] = this.groups[group].aggregates[index] / this.groups[group].rows.length;
                continue;
              }
              if (this.options.columns[index].aggregate === 'industry') {
                if (index === row.groups.appMarqCriterion.gapColumnNumber) {
                  if (row.groups.appMarqCriterion.filter) {
                    this.groups[group].aggregates[index] = "N/A";
                    continue;
                  } else {
                    this.groups[group].aggregates[index] = (Math.floor(this.groups[group].aggregates[row.groups.appMarqCriterion.complianceColumnNumber] * 100) - Math.round(this.groups[group].aggregates[row.groups.appMarqCriterion.appMarqcolumnNumber])) / 100;
                    continue;
                  }
                }
              }
              if (_.isFunction(this.options.columns[index].aggregate)) {
                this.groups[group].aggregates[index] = this.options.columns[index].aggregate(group, row.groups);
                continue;
              }
              if (row.groups[this.options.columns[index].aggregate] != null) {
                this.groups[group].aggregates[index] = row.groups[this.options.columns[index].aggregate];
                if (row.groups[this.options.columns[index].aggregate][group] != null) {
                  this.groups[group].aggregates[index] = row.groups[this.options.columns[index].aggregate][group];
                }
              }
            }
            if (this.groups[group].aggregates[0] === 0) {
              this.groups[group].aggregates[0] = group;
            }
            if (oldGroups != null) {
              this.groups[group].closed = (ref7 = oldGroups[group]) != null ? ref7.closed : void 0;
            }
          }
          if ((options != null ? options.sort : void 0) != null) {
            direction = options.sort.direction;
            columnIndex = options.sort.column;
            groups = [];
            for (group in this.groups) {
              groups.push({
                key: group,
                group: this.groups[group]
              });
            }
            groups.sort(function(group1, group2) {
              var v1, v2;
              v1 = group1.group.aggregates[columnIndex];
              v2 = group2.group.aggregates[columnIndex];
              if (isNaN(v1) || isNaN(v2)) {
                if (direction) {
                  if (v1 < v2) {
                    return 1;
                  } else {
                    return -1;
                  }
                } else {
                  if (v1 < v2) {
                    return -1;
                  } else {
                    return 1;
                  }
                }
              } else {
                if (direction) {
                  return v2 - v1;
                } else {
                  return v1 - v2;
                }
              }
            });
            this.groups = {};
            for (o = 0, len2 = groups.length; o < len2; o++) {
              group = groups[o];
              this.groups[group.key] = group.group;
            }
          } else {
            for (index = p = 0, ref8 = this.options.columns.length - 1; 0 <= ref8 ? p <= ref8 : p >= ref8; index = 0 <= ref8 ? ++p : --p) {
              if (this.options.columns[index].header === this.options.sortByDefault) {
                direction = false;
                columnIndex = index;
                groups = [];
                for (group in this.groups) {
                  groups.push({
                    key: group,
                    group: this.groups[group]
                  });
                }
                groups.sort(function(group1, group2) {
                  var v1, v2;
                  v1 = group1.group.aggregates[columnIndex];
                  v2 = group2.group.aggregates[columnIndex];
                  if (isNaN(row.columns[columnIndex])) {
                    if (direction) {
                      if (v1 < v2) {
                        return 1;
                      } else {
                        return -1;
                      }
                    } else {
                      if (v1 < v2) {
                        return -1;
                      } else {
                        return 1;
                      }
                    }
                  } else {
                    if (direction) {
                      return v1 - v2;
                    } else {
                      return v2 - v1;
                    }
                  }
                });
                this.groups = {};
                for (q = 0, len3 = groups.length; q < len3; q++) {
                  group = groups[q];
                  this.groups[group.key] = group.group;
                }
                break;
              }
            }
          }
        } else {
          this.groups = null;
        }
        that = this;
        html = this.$el.html(this.template({
          click: this.options.click != null,
          columns: this.options.columns,
          groups: this.groups,
          lastColumnAggregate: this.options.lastColumnAggregate,
          rows: this.options.rows.toJSON(),
          rowSelector: this.options.rowSelector
        }, {
          helpers: {
            processSpecialCharacters: function(headerMin) {
              if (headerMin == null) {
                return '';
              }
              return headerMin.replace(/#/g, '&#');
            },
            length: function(array, shift) {
              if ((array != null ? array.length : void 0) != null) {
                return array.length + shift;
              }
              return void 0;
            },
            setGroupKey: function(key) {
              that.groupKey = key;
            },
            setRowIndex: function(value) {
              that.rowIndex = value;
            },
            setSelected: function(item) {
              if (item.selected) {
                return 'selected';
              } else {
                return '';
              }
            },
            aggregateColumn: (function(_this) {
              return function(index, value) {
                var column, error, prefix, ref9;
                column = _this.options.columns[index];
                if (_.isUndefined(column) || column === null) {
                  return;
                }
                prefix = '';
                if ((ref9 = column.aggregate) === "sum" || ref9 === "average") {
                  prefix = column.aggregate + ': ';
                }
                if (column.format == null) {
                  return prefix + value;
                }
                if (_.isFunction(column.format)) {
                  try {
                    return prefix + column.format.call(_this, value);
                  } catch (_error) {
                    error = _error;
                    return prefix + numeral(value).format('0,000.0');
                  }
                }
                return prefix + numeral(value).format(column.format);
              };
            })(this),
            showAggregate: function(index, options) {
              var column;
              if (index === 0) {
                return;
              }
              column = that.options.columns[index];
              if (column.aggregate !== 'none') {
                return options.fn(this);
              }
              return options.inverse(this);
            },
            formatRow: (function(_this) {
              return function(value, columnId) {
                var column, item;
                column = _this.options.columns[columnId];
                if (_.isUndefined(column) || column === null) {
                  return;
                }
                if (column.format == null) {
                  return value;
                }
                if (_.isFunction(column.format)) {
                  item = _this.groups != null ? _this.groups[that.groupKey].rows[that.rowIndex] : _this.options.rows.at(that.rowIndex);
                  if (item.toJSON != null) {
                    item = item.toJSON();
                  }
                  return column.format.call(_this, value, columnId, that.rowIndex, item);
                }
                return numeral(value).format(column.format);
              };
            })(this),
            setAlignment: (function(_this) {
              return function(columnId) {
                var column;
                column = _this.options.columns[columnId];
                if (_.isUndefined(column) || column === null) {
                  return;
                }
                if (column.align != null) {
                  return column.align;
                }
                return 'left';
              };
            })(this),
            setLength: (function(_this) {
              return function(columnId) {
                var column;
                column = _this.options.columns[columnId];
                if (_.isUndefined(column) || column === null) {
                  return;
                }
                if (column.length != null) {
                  return ' length-' + column.length;
                } else {
                  return '';
                }
              };
            })(this)
          }
        }));
        that = this;
        for (i = r = 0, ref9 = this.options.columns.length - 1; 0 <= ref9 ? r <= ref9 : r >= ref9; i = 0 <= ref9 ? ++r : --r) {
          column = this.options.columns[i];
          if (column.selector != null) {
            $colspan = html.find('span[data-column=' + i + ']');
            items = [];
            ref10 = column.selector.data;
            fn = function(data, column) {
              return items.push({
                text: data.label,
                action: function() {
                  if (data.value != null) {
                    $colspan.addClass('active');
                    column.selector.active = true;
                  } else {
                    $colspan.removeClass('active');
                    column.selector.active = false;
                  }
                  return column.selector.onSelection(data.value);
                }
              });
            };
            for (s = 0, len4 = ref10.length; s < len4; s++) {
              data = ref10[s];
              fn(data, column);
            }
            $colspan.each(function(index, item) {
              var $span, selector;
              $span = $(item);
              selector = new bootstrap.Menu({
                text: $span.attr('data-label'),
                items: items
              });
              $span.html(selector.render());
              return selector.on('selection', column.selector.onSelection);
            });
          }
        }
        this.$el.data('bootstrap-table', this);
        return html;
      },
      adjustStickyHeader: function($container) {
        var $oth, $othth, $sticky, height, ref, root, top;
        top = (ref = this.$el.position()) != null ? ref.top : void 0;
        $sticky = this.$el.find('.invisible-sticky-scroll');
        root = $container != null ? $container.offset().top : 0;
        if (top >= 0) {
          $sticky.hide();
          return;
        }
        height = this.$el.height() + top;
        if (height < 0) {
          $sticky.hide();
          return;
        }
        $sticky.css('top', root);
        $sticky.show();
        $oth = this.$el.find('thead');
        $othth = $oth.find('th');
        $sticky.find('th').each(function(index, item) {
          return $(item).width($($othth[index]).width());
        });
        return $sticky.width($oth.find('thead').width());
      },
      openOrCloseGroup: function(event) {
        var $el, $group, groupKey, onExpandOrCollapse, ref, ref1;
        $group = $(event.target);
        groupKey = $group.attr('group-index');
        if ($group.hasClass('opened')) {
          $group.removeClass('opened');
          this.$el.find('.in-group[group-index="' + groupKey + '"]').addClass('closed');
          if ((ref = this.groups[groupKey]) != null) {
            ref.closed = true;
          }
        } else {
          $group.addClass('opened');
          this.$el.find('.in-group[group-index="' + groupKey + '"]').removeClass('closed');
          if ((ref1 = this.groups[groupKey]) != null) {
            ref1.closed = false;
          }
        }
        $el = this.$el.find('.in-group[group-index="' + groupKey + '"]:first');
        onExpandOrCollapse = (function(_this) {
          return function(e) {
            $el.off('webkitAnimationEnd oanimationend msAnimationEnd animationend transitionend webkitTransitionEnd oTransitionEnd MSTransitionEnd', onExpandOrCollapse);
            return _this.trigger('table:resized');
          };
        })(this);
        return $el.on('webkitAnimationEnd oanimationend msAnimationEnd animationend transitionend webkitTransitionEnd oTransitionEnd MSTransitionEnd', onExpandOrCollapse);
      },
      collapseAllGroup: function() {
        var groupItem, groupKey, groups, j, len, ref, results;
        groups = this.$el.find('.group');
        groups.removeClass('opened');
        this.$el.find('.in-group').addClass('closed');
        if (this.groups != null) {
          results = [];
          for (j = 0, len = groups.length; j < len; j++) {
            groupItem = groups[j];
            groupKey = $(groupItem).attr('group-index');
            results.push((ref = this.groups[groupKey]) != null ? ref.closed = true : void 0);
          }
          return results;
        }
      },
      expandGroup: function(groupKey) {
        var ref;
        this.$el.find('.group[group-index="' + groupKey + '"]').addClass('opened');
        this.$el.find('.in-group[group-index="' + groupKey + '"]').removeClass('closed');
        return (ref = this.groups[groupKey]) != null ? ref.closed = false : void 0;
      },
      actionOnRow: function(event) {
        var $tr;
        $tr = $(event.target).parents('tr');
        return this._applySelection($tr);
      },
      _applySelection: function($tr, silent) {
        var groupKey, item, originalItem, rowIndex;
        groupKey = $tr.attr('group-index');
        rowIndex = $tr.attr('data-index');
        item = this.options.rows.at(rowIndex).attributes;
        if (this.groups != null) {
          item = this.groups[groupKey].rows[rowIndex];
          originalItem = this.options.rows.findWhere({
            '_bootstrapTableId': item._bootstrapTableId
          });
        }
        if (!item.notSelectable) {
          if (this.options.selectOnClick) {
            this._unSelectAll();
            $tr.addClass('selected');
            item.selected = true;
            if (originalItem != null) {
              originalItem.set('selected', true);
            }
          }
          if (!silent) {
            this.trigger('row:clicked', item);
          }
          if (typeof this.options.click === 'function') {
            return this.options.click(item);
          }
        }
      },
      _unSelectAll: function() {
        var groupKey, j, len, ref, results, row;
        this.$el.find('tr').removeClass('selected');
        ref = this.options.rows.models;
        for (j = 0, len = ref.length; j < len; j++) {
          row = ref[j];
          row.set('selected', false);
        }
        if (this.groups != null) {
          results = [];
          for (groupKey in this.groups) {
            results.push((function() {
              var k, len1, ref1, results1;
              ref1 = this.groups[groupKey];
              results1 = [];
              for (k = 0, len1 = ref1.length; k < len1; k++) {
                row = ref1[k];
                results1.push(row.selected = false);
              }
              return results1;
            }).call(this));
          }
          return results;
        }
      },
      selectRow: function(rowIndex, silent) {
        var $tr;
        $tr = this.$el.find('tr[data-index=' + rowIndex + ']');
        if ($tr.length === 0) {
          return this._unSelectAll();
        }
        return this._applySelection($tr, silent);
      },
      select: function(key, value, silent) {
        var $tr, index, j, len, ref, ref1, row;
        if (value == null) {
          return this._unSelectAll();
        }
        index = 0;
        ref = this.options.rows.models;
        for (j = 0, len = ref.length; j < len; j++) {
          row = ref[j];
          if (((ref1 = row.get('extra')) != null ? ref1[key] : void 0) === value) {
            $tr = this.$el.find('tr[data-index=' + index + ']');
            return this._applySelection($tr, silent);
          }
          index++;
        }
      },
      resetSort: function() {
        var column, j, len, ref, results;
        ref = this.options.columns;
        results = [];
        for (j = 0, len = ref.length; j < len; j++) {
          column = ref[j];
          results.push(column.order = null);
        }
        return results;
      },
      sortColumn: function(event) {
        var $column, base, columnIndex, disabledIds, goDown, isChecked, ref, rows, sortComparator;
        $column = $(event.target).is('span') ? $(event.target) : $(event.target).parent();
        goDown = $column.hasClass('sort-up') || !$column.hasClass('sort-down');
        columnIndex = $column.attr('data-column');
        if (this.options.columns[columnIndex].selector == null) {
          if (typeof (base = this.options.columns[columnIndex]).preSort === "function") {
            base.preSort();
          }
        }
        sortComparator = function(row1, row2, goDown) {
          if (row1.columns[columnIndex] < row2.columns[columnIndex]) {
            return 1;
          }
          if (row1.columns[columnIndex] > row2.columns[columnIndex]) {
            return -1;
          }
          return 0;
        };
        if (((ref = this.options.columns[columnIndex]) != null ? ref.sort : void 0) != null) {
          sortComparator = this.options.columns[columnIndex].sort;
        }
        if (goDown) {
          this.options.rows.comparator = function(row1, row2) {
            return sortComparator(row1.toJSON(), row2.toJSON(), goDown);
          };
        } else {
          this.options.rows.comparator = function(row1, row2) {
            return -sortComparator(row1.toJSON(), row2.toJSON(), goDown);
          };
        }
        this.resetSort();
        this.options.columns[columnIndex].order = goDown ? 'sort-down' : 'sort-up';
        this.options.rows.sort();
        this.options.rows.comparator = null;
        disabledIds = _.map(_.filter(this.$el.find('table tbody tr'), function(row) {
          if ($(row).find('td:first').hasClass('hide-row')) {
            return row;
          }
        }), function(rowId) {
          return $(rowId).attr('data-id');
        });
        isChecked = this.$el.find('thead .row-selector input').first().is(':checked');
        this.render({
          sort: {
            direction: goDown,
            column: columnIndex
          }
        });
        if (isChecked) {
          this.$el.find('table thead tr th.row-selector input[type="checkbox"]').prop('checked', true);
        }
        rows = this.options.rows;
        this.$el.find('table tbody tr td.center').last().addClass('violation-body-size');
        this.$el.find('table thead tr:first th.center').last().addClass('violation-header-size');
        _.each(this.$el.find('table tbody tr'), (function(_this) {
          return function(row) {
            if (_.contains(disabledIds, $(row).attr('data-id'))) {
              return $(row).find('td:first').addClass('hide-row');
            }
          };
        })(this));
        this.$el.find('.row-selector.hide-row input[type="checkbox"]').prop('checked', false);
        if (this.$el.find('.hide-row').length > 0) {
          _.each(this.$el.find('.hide-row'), (function(dom) {
            this.options.rows.findWhere({
              id: dom.parentElement.dataset.id
            }).set('rowSelected', false);
          }), this);
        }
        this.$el.find('.row-selector.hide-row').on('click', function() {
          return false;
        });
        this.$el.find('th.row-selector.disabled').on('click', function() {
          return false;
        });
        return this.trigger('sorted');
      },
      update: function(options) {
        var hasRowSelected, i, id, index, j, k, l, len, len1, len2, len3, len4, m, n, o, ref, ref1, ref2, ref3, row, rowsToAdd, rowsToRemove, same, sameRow;
        if (options.rows == null) {
          return;
        }
        options = _.extend({
          resetRowSelector: false
        }, options);
        rowsToAdd = [];
        rowsToRemove = [];
        ref = this.options.rows.models;
        for (j = 0, len = ref.length; j < len; j++) {
          row = ref[j];
          id = row.get('id');
          sameRow = options.rows.findWhere({
            id: id
          });
          if (sameRow == null) {
            rowsToRemove.push(row);
          }
        }
        for (k = 0, len1 = rowsToRemove.length; k < len1; k++) {
          row = rowsToRemove[k];
          this.options.rows.remove(row);
        }
        if (options.resetRowSelector) {
          ref1 = options.rows.models;
          for (l = 0, len2 = ref1.length; l < len2; l++) {
            row = ref1[l];
            id = row.get('id');
            sameRow = this.options.rows.findWhere({
              id: id
            });
            if (sameRow != null) {
              index = this.options.rows.indexOf(sameRow);
              this.options.rows.remove(sameRow);
              this.options.rows.add(row, {
                at: index
              });
            } else {
              rowsToAdd.push(row);
            }
          }
        } else {
          hasRowSelected = false;
          ref2 = options.rows.models;
          for (m = 0, len3 = ref2.length; m < len3; m++) {
            row = ref2[m];
            id = row.get('id');
            sameRow = this.options.rows.findWhere({
              id: id
            });
            if (sameRow != null) {
              same = true;
              if (sameRow.get('rowSelected')) {
                hasRowSelected = true;
              }
              for (i = n = 0, ref3 = row.get('columns').length - 1; 0 <= ref3 ? n <= ref3 : n >= ref3; i = 0 <= ref3 ? ++n : --n) {
                if (!same) {
                  break;
                }
                same = row.get('columns')[i] === sameRow.get('columns')[i];
              }
              if (!same) {
                index = this.options.rows.indexOf(sameRow);
                this.options.rows.remove(sameRow);
                this.options.rows.add(row, {
                  at: index
                });
              }
            } else {
              rowsToAdd.push(row);
            }
          }
          this.trigger('update:row-selector', {
            hasChecked: hasRowSelected
          });
        }
        for (o = 0, len4 = rowsToAdd.length; o < len4; o++) {
          row = rowsToAdd[o];
          this.options.rows.add(row);
        }
        this.resetSort();
        return this.render();
      }
    });
  };

  TreeExplorer = function($, _, Backbone, Handlebars, numeral) {
    var Node, Nodes, NodesView, TreeView;
    Node = Backbone.Model.extend({
      url: function() {
        if (window.REST_URL != null) {
          return window.REST_URL + this.get('href');
        }
        return this.get('href');
      },
      defaults: {
        display: true
      }
    });
    Nodes = Backbone.Collection.extend({
      model: Node,
      url: function() {
        var paginate;
        paginate = this.startRow != null ? '?startRow=' + this.startRow : '';
        paginate += this.nbRows != null ? '&nbRows=' + this.nbRows : '';
        if (window.REST_URL != null) {
          return window.REST_URL + this.href + paginate;
        }
        return this.href + paginate;
      },
      initialize: function(options) {
        this.href = options != null ? options.href : void 0;
        this.selected = options != null ? options.selected : void 0;
        this.startRow = options != null ? options.startRow : void 0;
        return this.nbRows = options != null ? options.nbRows : void 0;
      }
    });
    NodesView = Backbone.View.extend({
      tagName: 'ul',
      template: Handlebars.compile('{{#each nodes}} <li  {{#unless display}}class="hide"{{/unless}}><div data-level="{{../level}}" class="node"> <div class="node-container"> <span class="{{#isLeaf children}}node-leaf{{else}}node-icon node-button{{/isLeaf}}" data-href="{{children.href}}"></span> <span data-id="{{href}}" class="name">{{name}}</span> </div> </div><div class="children closed"></div> </li> {{/each}} {{#if hasMoreNodes}} <li><div data-level="{{level}}" class="node"> <div class="node-container"> <span class="node-icon node-loading"></span> <span class="node-loading-text">Loading next items</span> </div> </div> </li> {{/if}}'),
      events: {
        'click span.node-button': 'openOrCloseNode',
        'click span.name': 'selectNode'
      },
      loadOnVisibleScroll: function(data) {
        var $li, nextNodes, nodeOffset, ref, ref1, visible;
        $li = this.$el.find('> li >>> span.node-loading-text');
        nodeOffset = (ref = $li.offset()) != null ? ref.top : void 0;
        if (nodeOffset == null) {
          return;
        }
        visible = (0 < (ref1 = nodeOffset - data.containerOffset) && ref1 < data.containerHeight) && $li.parents('.children.closed').length === 0;
        if (this.loading) {
          return;
        }
        if (visible) {
          this.loading = true;
          nextNodes = new Nodes({
            href: this.nodes.href,
            startRow: this.nodes.startRow + this.nodes.nbRows - 1,
            nbRows: this.nodes.nbRows
          });
          return nextNodes.fetch().done((function(_this) {
            return function() {
              var duplicate;
              if (_this.initiallySelected != null) {
                duplicate = nextNodes.findWhere({
                  href: _this.initiallySelected
                });
                if (duplicate != null) {
                  duplicate.set('display', false);
                }
              }
              _this.renderMoreContent(nextNodes);
              _this.nodes.add(nextNodes.toJSON());
              _this.nodes.startRow = nextNodes.startRow;
              _this.loading = false;
              return _this.tree.loadingItem();
            };
          })(this));
        }
      },
      selectNode: function(event) {
        var $target;
        $target = $(event.target);
        return this._selectNode($target);
      },
      _selectNode: function($target) {
        var $node;
        $node = $($target.parents('div.node').get(0));
        if (this.level !== parseInt($node.attr('data-level'))) {
          return;
        }
        return this._updateSelection($target);
      },
      _updateSelection: function($target) {
        var $node, href, node;
        $node = $($target.parents('div.node').get(0));
        this.tree.trigger('node:unselected');
        $node.addClass('selected');
        href = $target.attr('data-id');
        node = this.nodes.findWhere({
          href: href
        });
        if (node == null) {
          return;
        }
        return this.tree.trigger('node:clicked', node.toJSON());
      },
      openOrCloseNode: function(event) {
        return this._openOrCloseNode({
          $target: $(event.target)
        });
      },
      _openOrCloseNode: function(options, callback) {
        var $children, $li, $node, $target, base, base1, children, emptyContent, that;
        $target = options.$target;
        $node = $($target.parents('div.node').get(0));
        if (this.level !== parseInt($node.attr('data-level'))) {
          return;
        }
        $li = $($target.parents('li').get(0));
        $children = $($li.find('div.children').get(0));
        if ($target.hasClass('open')) {
          if (options.keepOpen) {
            return typeof callback === "function" ? callback() : void 0;
          }
          $children.addClass('closed');
          $target.removeClass('open');
          if (typeof (base = this.tree.options).animate === "function") {
            base.animate($children, 'close');
          }
          if ($li.find('div.node.selected').length) {
            this._updateSelection($node.find('span.name'));
          }
          return;
        }
        emptyContent = ['', '<ul></ul>'];
        if (emptyContent.indexOf($children.html()) < 0) {
          $children.removeClass('closed');
          $target.addClass('open');
          if (typeof (base1 = this.tree.options).animate === "function") {
            base1.animate($children, 'open');
          }
          return;
        }
        children = new Nodes({
          href: $target.attr('data-href'),
          startRow: this.startRow,
          nbRows: this.nbRows
        });
        this.children = children;
        that = this;
        return children.fetch({
          success: function() {
            var base2, parent, target;
            children.view = new NodesView({
              tree: that.tree,
              level: that.level + 1,
              nodes: children,
              startRow: that.startRow,
              nbRows: that.nbRows
            });
            if (options.parent) {
              parent = children.findWhere({
                href: options.parent.get('href')
              });
              if (parent == null) {
                children.view.initiallySelected = options.parent.get('href');
                children.unshift(options.parent);
                children.pop();
                children.startRow -= 1;
              }
            } else {
              if (options.parents != null) {
                target = options.parents.at(options.parents.length - 1);
                parent = children.findWhere({
                  href: target.get('href')
                });
                if (parent == null) {
                  children.view.initiallySelected = target.get('href');
                  children.unshift(target);
                  children.pop();
                  children.startRow -= 1;
                }
              }
            }
            $children.html(children.view.render());
            $children.removeClass('closed');
            if (children.length !== 0) {
              $target.addClass('open');
            }
            if (typeof (base2 = that.tree.options).animate === "function") {
              base2.animate($children, 'open');
            }
            that.tree.loadingItem();
            return typeof callback === "function" ? callback(children.view) : void 0;
          }
        });
      },
      _scrollToSelected: function($target) {
        var ref, scrollOffset;
        scrollOffset = Math.max(0, ((ref = $target.position()) != null ? ref.top : void 0) - 16);
        return $($target.parents('div.tree-container')[0]).animate({
          scrollTop: scrollOffset
        }, '400', 'swing');
      },
      initialize: function(options) {
        this.tree = options.tree;
        this.nodes = options.nodes;
        this.level = options.level || 0;
        this.startRow = options.startRow;
        this.nbRows = options.nbRows;
        return this.tree.on('scroll:container', this.loadOnVisibleScroll, this);
      },
      openPaths: function(depth) {
        var href, j, len, node, ref, results;
        if (depth <= 0) {
          return;
        }
        ref = this.nodes.models;
        results = [];
        for (j = 0, len = ref.length; j < len; j++) {
          node = ref[j];
          href = node.get('children').href;
          results.push(this._openOrCloseNode({
            $target: this.$el.find('span.node-button[data-href="' + href + '"]'),
            keepOpen: true
          }, (function(_this) {
            return function(subView) {
              if (subView == null) {
                return;
              }
              return subView.openPaths(depth - 1);
            };
          })(this)));
        }
        return results;
      },
      loadPath: function(parents, depth, callback) {
        var $target, href, parentHref, ref;
        if (parents.length - 1 <= depth) {
          href = parents.selected;
          $target = this.$el.find('span.name[data-id="' + href + '"]');
          this._selectNode($target);
          this._scrollToSelected($target);
          return typeof callback === "function" ? callback() : void 0;
        }
        parentHref = (ref = parents.at(depth).get('children')) != null ? ref.href : void 0;
        if (parentHref == null) {
          return;
        }
        return this._openOrCloseNode({
          $target: this.$el.find('span.node-button[data-href="' + parentHref + '"]'),
          parent: parents.at(depth + 1),
          parents: parents,
          depth: depth + 1
        }, (function(_this) {
          return function(view) {
            return view.loadPath(parents, depth + 1, callback);
          };
        })(this));
      },
      render: function() {
        var hasMoreNodes;
        hasMoreNodes = this.nodes.nbRows === this.nodes.length;
        if (hasMoreNodes) {
          this.nodes.remove(this.nodes.at(this.nodes.length - 1));
        }
        this.$el.html(this.template({
          level: this.level,
          hasMoreNodes: hasMoreNodes,
          nodes: this.nodes.toJSON()
        }, {
          helpers: {
            isLeaf: function(children, options) {
              if (children == null) {
                return options.fn(this);
              }
              return options.inverse(this);
            }
          }
        }));
        return this.$el;
      },
      renderMoreContent: function(nodes) {
        var hasMoreNodes;
        hasMoreNodes = nodes.nbRows === nodes.length;
        if (hasMoreNodes) {
          nodes.remove(nodes.at(nodes.length - 1));
        }
        this.$el.find('li').last().replaceWith(this.template({
          level: this.level,
          hasMoreNodes: hasMoreNodes,
          nodes: nodes.toJSON()
        }, {
          helpers: {
            isLeaf: function(children, options) {
              if (children == null) {
                return options.fn(this);
              }
              return options.inverse(this);
            }
          }
        }));
        return this.$el;
      }
    });
    TreeView = Backbone.View.extend({
      tagName: 'div',
      className: 'tree',
      template: Handlebars.compile('<div class="tree-header">{{title}}</div><div class="tree-container"></div>'),
      loadingItem: function() {
        var containerHeight, containerOffset, ref;
        containerOffset = (ref = this.$el.find('.tree-container').offset()) != null ? ref.top : void 0;
        containerHeight = this.$el.find('.tree-container').outerHeight();
        return this.trigger('scroll:container', {
          containerOffset: containerOffset,
          containerHeight: containerHeight
        });
      },
      initialize: function(options) {
        var j, len, nodeHref, ref;
        this.options = _.extend({}, this.options, options);
        if (this.options.nbRows != null) {
          this.options.nbRows = parseInt(this.options.nbRows) + 1;
        }
        this.nodes = [];
        ref = this.options.roots;
        for (j = 0, len = ref.length; j < len; j++) {
          nodeHref = ref[j];
          this.nodes.push(new Nodes({
            href: nodeHref
          }));
        }
        this.on('node:unselected', this.unSelectNodes, this);
        return this;
      },
      unSelectNodes: function() {
        return this.$el.find('div.node.selected').removeClass('selected');
      },
      _expand: function() {
        var j, len, nodeNodes, ref, results;
        if (this.options.expand) {
          ref = this.nodes;
          results = [];
          for (j = 0, len = ref.length; j < len; j++) {
            nodeNodes = ref[j];
            results.push(nodeNodes.view.openPaths(this.options.expand));
          }
          return results;
        }
      },
      render: function() {
        var j, len, promise, promises, ref, rootNodes, that;
        this.$el.find('.tree-container').off('scroll');
        this.$el.html(this.template({
          title: this.options.title
        }));
        this.$el.find('.tree-container').on('scroll', (function(_this) {
          return function() {
            return _this.loadingItem();
          };
        })(this));
        promises = null;
        ref = this.nodes;
        for (j = 0, len = ref.length; j < len; j++) {
          rootNodes = ref[j];
          promise = rootNodes.fetch();
          if (promises == null) {
            promises = promise;
          } else {
            promises = $.when(promises, promise);
          }
        }
        that = this;
        promises.done(function() {
          var k, len1, ref1, selectedNode, selectionPath;
          ref1 = that.nodes;
          for (k = 0, len1 = ref1.length; k < len1; k++) {
            rootNodes = ref1[k];
            rootNodes.view = new NodesView({
              tree: that,
              nodes: rootNodes,
              nbRows: that.options.nbRows,
              startRow: that.options.startRow
            });
            that.$el.find('.tree-container').append(rootNodes.view.render());
          }
          if (that.options.selectedNode != null) {
            selectedNode = new Node({
              href: that.options.selectedNode
            });
            selectionPath = new Nodes({
              selected: that.options.selectedNode,
              href: that.options.selectedNode + '/ancestors'
            });
            return $.when(selectedNode.fetch({
              cache: false
            }), selectionPath.fetch({
              cache: false
            })).done(function() {
              var l, len2, nodeHref, nodeNodes, ref2, rootPath;
              selectionPath.add(selectedNode);
              ref2 = that.nodes;
              for (l = 0, len2 = ref2.length; l < len2; l++) {
                nodeNodes = ref2[l];
                nodeHref = nodeNodes.href;
                if (selectionPath.length === 0) {
                  return nodeNodes.view.loadPath(selectionPath, 1, function() {
                    return that._expand();
                  });
                } else {
                  rootPath = selectionPath.at(0);
                  if (nodeHref === rootPath.get('href')) {
                    return nodeNodes.view.loadPath(selectionPath, 0, function() {
                      return that._expand();
                    });
                  }
                }
              }
            });
          }
        });
        return this.$el;
      }
    });
    return TreeView;
  };

  ellipsis = function(value, maxlength) {
    if (value.length > maxlength) {
      return value.slice(0, maxlength - 1) + '...';
    }
    return value;
  };

  closableItems = {
    items: [],
    addItem: function(item) {
      if (item.close != null) {
        return this.items.push(item);
      }
    },
    removeItem: function(item) {
      var index;
      index = _.indexOf(this.items, item);
      if (index > -1) {
        return this.items.splice(index, 1);
      }
    },
    close: function(excludedItem) {
      var item, j, len, ref, results;
      ref = this.items;
      results = [];
      for (j = 0, len = ref.length; j < len; j++) {
        item = ref[j];
        if (item !== excludedItem) {
          results.push(item != null ? item.close() : void 0);
        } else {
          results.push(void 0);
        }
      }
      return results;
    }
  };


  /*
    bootstrap provides generic and reusable backbone view bootstrap:
    Dependencies:
      - jquery >= 1.10.1
      - underscore >= 1.4.4
      - backbone >= 1.0.0
      - handlebars >= 1.0.0
      - cast-scroll (Scroller)
        - jquery.mousewheel >= 3.1.3
        - jquery-ui >= 1.10.3
   */

  bootstrap = function($, _, Backbone, Handlebars, numeral) {
    var ipadHelper;
    ipadHelper = {
      isIpad: function() {
        return navigator.userAgent.match(/iPad/i) !== null;
      }
    };
    bootstrap = {};
    bootstrap.Table = Table($, _, Backbone, Handlebars, numeral, ipadHelper);
    bootstrap.TreeExplorer = TreeExplorer($, _, Backbone, Handlebars, numeral, ipadHelper);
    bootstrap.Menu = Menu($, _, Backbone, Handlebars, ipadHelper);
    bootstrap.Selector = Selector($, _, Backbone, Handlebars, ipadHelper);
    return bootstrap;
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['jquery', 'underscore', 'backbone', 'handlebars', 'numberFormater'], function($, _, Backbone, Handlebars, numeral) {
      return bootstrap($, _, Backbone, Handlebars, numeral);
    });
  } else if (typeof window !== "undefined" && window !== null) {
    window.bootstrap = bootstrap($, _, Backbone, Handlebars, numeral);
  }

}).call(this);
