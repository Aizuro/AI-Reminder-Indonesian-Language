from transformers import AutoModelForTokenClassification, AutoTokenizer
import torch

from .token_utils import merge_subwords


class ReminderNERModel:
    def __init__(self, model_path: str = "model/checkpoint"):
        self.model_path = model_path
        self.device = torch.device(
            'cuda' if torch.cuda.is_available() else 'cpu')

        self.model = AutoModelForTokenClassification.from_pretrained(
            model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)

        self.model.to(self.device)
        self.model.eval()

        # Get label list from config
        self.label_list = self.model.config.id2label

    def predict(self, text: str) -> dict:
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(self.device)

        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.argmax(outputs.logits, dim=-1)

        # Convert to labels
        tokens = self.tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
        labels = [self.label_list[pred.item()] for pred in predictions[0]]

        # Remove special tokens ([CLS], [SEP], [PAD]) and merge ## subwords
        # into whole words (label = label of the first subword)
        tokens_clean, labels_clean = merge_subwords(tokens, labels)

        # Extract entities
        entities = self._extract_entities(tokens_clean, labels_clean)

        # Calculate confidence
        confidence = self._calculate_confidence(outputs.logits)

        return {
            'tokens': tokens_clean,
            'labels': labels_clean,
            'entities': entities,
            'confidence': confidence
        }

    def _extract_entities(self, tokens: list, labels: list) -> list:
        entities = []
        current_entity = None

        for token, label in zip(tokens, labels):
            if label.startswith('B-'):
                # Save previous entity
                if current_entity:
                    entities.append(current_entity)

                # Start new entity
                current_entity = {
                    'type': label[2:],
                    'text': token,
                    'tokens': [token]
                }

            elif label.startswith('I-') and current_entity:
                # Continue current entity
                current_entity['text'] += ' ' + token
                current_entity['tokens'].append(token)

            else:  # 'O' label
                # Save previous entity
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None

        # last entity
        if current_entity:
            entities.append(current_entity)

        return entities

    def _calculate_confidence(self, logits: torch.Tensor) -> float:
        """Calculate average confidence score"""
        probs = torch.softmax(logits, dim=-1)
        max_probs = torch.max(probs, dim=-1).values
        avg_confidence = torch.mean(max_probs).item()
        return avg_confidence
