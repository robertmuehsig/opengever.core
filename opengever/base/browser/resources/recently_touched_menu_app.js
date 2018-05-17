$(init);
function init() {
  var app = new Vue({
    template: '#recently-touched-menu-list',
    el: '#recently-touched-vue-app',
    data: {
      userid: null,
      i18n: {},
      recentlyTouched: [],
      checkedOut: [],
      isOpen: false,
    },

    beforeMount: function () {
      var portalurl = this.$el.attributes['data-portalurl'].value;
      this.userid = this.$el.attributes['data-userid'].value;
      this.endpoint = portalurl + '/@recently-touched/' + this.userid;
      this.i18n = JSON.parse(this.$el.attributes['data-i18n'].value);

      var requester = axios.create();
      requester.defaults.headers.common['Accept'] = 'application/json';
      requester.defaults.headers.common['Content-Type'] = 'application/json';
      this.requester = requester;
    },

    updated: function () {
      // Update relative times after DOM has been updated by Vue
      $(".recently-touched-menu .timeago").timeago();
    },

    methods: {
      isSameElement: function(target) {
        return target !== this.$el && !this.$el.contains(target);
      },
      handleClickOutside: function(event) {
        if (this.isSameElement(event.target)) {
          this.close();
        }
      },
      toggle: function() {
        if (this.isOpen) {
          return this.close();
        } else {
          return this.open();
        }
      },
      open: function() {
        return this.fetchData()
          .then(function() {
            this.isOpen = true;
          }.bind(this));
      },
      close: function() {
        this.isOpen = false;
      },
      fetchData: function () {
        return this.requester.get(this.endpoint)
          .then(function (response) {
            this.recentlyTouched = response.data['recently_touched'];
            this.checkedOut = response.data['checked_out'];
        }.bind(this));
      },
    },
    created: function() {
      document.addEventListener('click', this.handleClickOutside);
    }
  });
}
