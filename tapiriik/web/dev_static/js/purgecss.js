module.exports = {
    content: ['tapiriik/web/templates/*.html', 'tapiriik/web/templates/static/*.html', 'tapiriik/web/templates/diag/user_activities.html'],
    css: ['tapiriik/web/dev_static/css/dev_style.css'],
    output: 'tapiriik/web/static/css/style.css',
    keyframes: true,
    variables: true,
    safelist: ['active'],
    extractors: [
        {
            extractor: content => content.match(/[A-Za-z0-9-_:\/]+/g) || [],
            extensions: ['html']
        }
    ]
}