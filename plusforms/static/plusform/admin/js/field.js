jQuery(document).ready(function ($) {
    let form = $('form');
    let select = form.find('#id_field_type');
    let fieldset = form.find('.file_input--wrapper')
    let textset_textfield = form.find('.text_field--wrapper')
    let fieldset_img = form.find('.image_input--wrapper')
    let select_options_img = form.find('.select-options--wrapper')
    let required_checkbox = form.find('#id_required')[0]

    let tmpRequiredCheckedState = required_checkbox.checked

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

        if (value === "TextField" || value === "InputField") {
            textset_textfield.show()
        } else {
            textset_textfield.hide()
        }


        if (value === "CaptchaField") {
            required_checkbox.checked = true;
            required_checkbox.disabled = true;
        } else {
            required_checkbox.checked = tmpRequiredCheckedState;
            required_checkbox.disabled = false;
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
