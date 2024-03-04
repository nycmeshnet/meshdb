from django.forms import Widget

class PanoramaViewer(Widget):
    template_name="widgets/panorama_viewer.html"
    
    def render(self, name, value, attrs=None, renderer=None):
        # Get the value of the model field
        model_field_value = self.attrs.get('panoramas', None)
        print(f"bro wtf: {self.attrs}")
        print(f"bro wtf: {name}")
        print(f"bro wtf: {value}")

        # Now you can use the model_field_value as needed
        # For example, you can use it to modify the rendering of the widget
        if value:
            # Do something with model_field_value
            back = "<div style='display:flex; flex-direction: row; width:100%; overflow-x:auto; max-height:300px;'>"
            panos = value.split(',')
            for p in panos:
                back += f"<img src='{p}' height='300px'/>"
            back += "</div>"
            return back

        # Call the parent class' render method
        return super().render(name, value, attrs, renderer)

