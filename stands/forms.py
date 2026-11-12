from django import forms

from stands.models import Stand

# Максимальный размер загружаемого изображения: 2 МБ.
MAX_IMAGE_SIZE = 2 * 1024 * 1024


class StandForm(forms.ModelForm):
    """Форма создания и редактирования стенда с загрузкой изображения."""

    class Meta:
        model = Stand
        fields = ["name", "stand_type", "area", "image"]
        labels = {
            "name": "Название стенда",
            "stand_type": "Тип стенда",
            "area": "Площадь, кв.м",
            "image": "Изображение",
        }
        help_texts = {
            "image": "Необязательно. Допустимы изображения до 2 МБ.",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "stand_type": forms.Select(attrs={"class": "form-select"}),
            "area": forms.NumberInput(
                attrs={"class": "form-control", "step": "any"}
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }

    def clean_image(self):
        """Ограничить размер загружаемого файла."""
        image = self.cleaned_data.get("image")
        # Размер известен только у только что загруженного файла.
        if image and hasattr(image, "size") and image.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError(
                "Размер изображения не должен превышать 2 МБ."
            )
        return image
