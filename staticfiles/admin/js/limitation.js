(function () {
  function toggle() {
    const type = document.getElementById('id_type');
    if (!type) {
        return;
    }

    const fieldsets = ['posts_views', 'stats_views'];

    const config = {
      post_views: 'posts_views',
      language_stats: 'stats_views',
      views_by_source_stats: 'stats_views',
    }

    const currConfig = config[type.value];

    document.querySelectorAll(`fieldset.${currConfig}`).forEach(fs => {
      fs.style.removeProperty('display');
    });

    fieldsets.filter(fs => fs !== currConfig).forEach(fs => {
      document.querySelectorAll(`fieldset.${fs}`).forEach(fs => {
        fs.style.display = 'none';
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    toggle();
    const type = document.getElementById('id_type');
    if (type) {
      type.addEventListener('change', toggle);
    }
  });
})();
