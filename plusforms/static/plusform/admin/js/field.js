$(function () {
    let form = $('form');
    let select = form.find('#id_field_type');
    let fieldset = form.find('.file_input--wrapper')
    let fieldset_img = form.find('.image_input--wrapper')

    if (select.val() !== "FileField" && select.val() !== "ImageField") {
        fieldset.hide();
        fieldset_img.hide();
    }

    select.on('change',(e) => {
        let value = this.activeElement.value;

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
    });
});