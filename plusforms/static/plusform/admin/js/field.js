jQuery(document).ready(function ($) {
    let form = $('form');
    let select = form.find('#id_field_type');
    let fieldset = form.find('.file_input--wrapper')
    let fieldset_img = form.find('.image_input--wrapper')
    let select_options_img = form.find('.select-options--wrapper')

    trigger(select.val())

    select.on('change', (e) => {
        let value = this.activeElement.value;
        trigger(value)
    });

    function trigger(value) {
        if (value === "FileField" || value === "ImageField") {
            fieldset.show();
        } else {
            fieldset.hide();
        }

        if (value === "ImageField") {
            fieldset_img.show();
        } else {
            fieldset_img.hide()
        }

        if (value === "SelectField" || value === "SelectMultipleField") {
            select_options_img.show();
        } else {
            select_options_img.hide();
        }
    }
});
