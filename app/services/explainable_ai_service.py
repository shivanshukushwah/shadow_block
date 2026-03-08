# import shap  # Optional dependency - install with: pip install shap lime
# from lime.lime_text import LimeTextExplainer

class ExplainableAIService:
    def __init__(self, model, tokenizer, class_names):
        self.model = model
        self.tokenizer = tokenizer
        self.class_names = class_names

    def explain_with_shap(self, text):
        # Tokenize and predict
        explainer = shap.Explainer(self.model)
        shap_values = explainer([text])
        # Return SHAP values for visualization or further processing
        return shap_values

    def explain_with_lime(self, text):
        explainer = LimeTextExplainer(class_names=self.class_names)
        exp = explainer.explain_instance(
            text, 
            self.model.predict_proba, 
            num_features=10
        )
        # Return explanation as list of (word, importance) tuples
        return exp.as_list()