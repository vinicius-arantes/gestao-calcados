class BootstrapFormMixin:
    """Aplica as classes do Bootstrap 5 em todos os campos do formulário."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            tipo = getattr(campo.widget, 'input_type', None)
            if tipo == 'checkbox':
                classe = 'form-check-input'
            elif tipo == 'select':
                classe = 'form-select'
            else:
                classe = 'form-control'
            campo.widget.attrs.setdefault('class', classe)
